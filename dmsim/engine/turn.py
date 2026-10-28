"""ターン構造（500〜512）、カードの実行（601）、マナ支払い（112.2a）。

ターンはステップの列（data/rules/turn.yaml）で、各ステップの処理は @step で登録する。
ターンが始まる時に state.step_mods（効果による「飛ばす」「もう一度行う」）を反映した列を作る。
"""
from __future__ import annotations

import itertools

from ..types import CrossTask, PlayTask, TurnTask
from .registry import STEPS, step, task


class TurnMixin:
    def turn_task(self) -> dict:
        return {"t": "turn", "steps": self._build_steps(self.s.active), "i": 0, "sub": 0, "cp": True}

    def _build_steps(self, p: int) -> list[str]:
        """このターンのステップ列。使った step_mod は turns を 1 減らし、0 になったら消す。"""
        out = []
        for name in self.rules.steps:
            mods = [m for m in self.s.step_mods if m["player"] == p and m["step"] == name]
            if any(m["mode"] == "skip" for m in mods):
                pass
            else:
                out.append(name)
                out += [name for m in mods if m["mode"] == "extra"]
            for m in mods:
                m["turns"] -= 1
        self.s.step_mods = [m for m in self.s.step_mods if m["turns"] > 0]
        return out

    def _step_done(self, t):
        t["i"] += 1
        t["sub"] = 0

    def _expire(self, duration: str):
        """期限の切れた継続的効果を消す。修整が切れてパワー0以下になったら、その場で破壊する（703.4c）。
        状況起因処理のタスクを積むので、呼んだ側はこの後に自分のタスクを積まないこと。"""
        n = len(self.s.continuous)
        self.s.continuous = [c for c in self.s.continuous if c["duration"] != duration]
        self.s.delayed = [d for d in self.s.delayed if d["duration"] != duration]
        if len(self.s.continuous) != n:
            self._sba()

    def _distinct_hand_options(self, p, verb):
        """同じカード名の手札は区別しない（対称な選択肢の正規化）。"""
        seen, out = set(), []
        for cid in self.zlist("hand", p):
            dfn = self.s.cards[cid].defn
            if dfn not in seen:
                seen.add(dfn)
                out.append({"key": f"{verb}:{dfn}", "cid": cid, "name": self.cdef(cid).name})
        return out

    def _play_options(self, p) -> list[dict]:
        """メインステップで実行できるカード。ツインパクトは面ごとに別の選択肢（810.3）。"""
        out = []
        for o in self._distinct_hand_options(p, "play"):
            cid = o["cid"]
            d = self.cdef(cid)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                if not self._can_play_face(cid, p, fi):
                    continue
                key = o["key"] if fi is None else f"{o['key']}:{fi}"
                opt = {"key": key, "cid": cid, "name": f.name}
                if fi is not None:
                    opt["face"] = fi
                out.append(opt)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                if f.free_if and f.is_creature() and self.permits(cid, "summon") \
                        and self.eval_cond(f.free_if, {"you": p, "self": self.s.ref(cid), "vars": {}}):
                    opt = {"key": f"{o['key']}:free" if fi is None else f"{o['key']}:{fi}:free", "cid": cid,
                           "name": f.name, "free": True}   # G・ゼロ: コストを支払わずに召喚
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
        return out

    def _cross_options(self, p) -> list[dict]:
        """メインステップに、バトルゾーンのクロスギアのマナコストをもう一度支払って自分のクリーチャーにクロスする（303.3b, 504.2）。
        すでにクロスしているクリーチャー自身にはクロスしなおせない（303.4a）。"""
        out = []
        for g in self.bz_tops(p):
            if "cross_gear" not in self.chars(g)["types"]:
                continue
            cur = self.s.cards[g].crossed
            if not self._mana_choices(g, p, limit=1):
                continue
            for c in self.bz_tops(p):
                if "creature" in self.chars(c)["types"] and not (cur and cur == self.s.ref(c)):
                    out.append({"key": f"cross:{self.s.cards[g].defn}:{self.s.cards[c].defn}", "cid": g, "target": self.s.ref(c)})
        return out

    def _can_play_face(self, cid, p, face) -> bool:
        d = self.cdef(cid).face(face)
        action = "summon" if d.is_creature() else "generate" if d.is_permanent() else "cast"
        if not self.permits(cid, action) or (d.is_creature() and not self.permits(cid, "enter_bz")):
            return False
        if "evolution" in d.types:
            srcs = self._evo_sources(cid, p, face)
            if not srcs:
                return False
            n = len(srcs) if d.evolve_any else 1            # 最も安い組合せで払えるか（112.2b）
            cost = max(0, d.cost - n * d.cost_reduce_per_evo) if d.cost_reduce_per_evo else None
            return bool(self._mana_choices(cid, p, face, cost=self._opt_reduced(cid, face, d, self._sac_reduced(d, self._tap_reduced(d, p, cost, None), self._sac_pool(d, p))), limit=1))
        return bool(self._mana_choices(cid, p, face, cost=self._opt_reduced(cid, face, d, self._sac_reduced(d, self._tap_reduced(d, p, None, None), self._sac_pool(d, p))), limit=1))

    def _opt_reduced(self, cid, face, d, cost):
        """B・A・D / J・O・E: 減らして実行できる場合の最安コスト（実行可能かの判定用）。"""
        o = self.chars(cid, face)["opt_reduce"]
        return cost if not o else max(0, (d.cost if cost is None else cost) - o["amount"])

    def _sac_pool(self, d, p) -> list[int]:
        """ササゲール: ディスペクターを召喚する時、破壊してコストを減らせる自分のクリーチャー。"""
        if not any("ディスペクター" in r for r in d.races):
            return []
        return [c for c in self.bz_tops(p) if self.chars(c)["sac_reduce"] > 0]

    def _sac_reduced(self, d, cost, sacs):
        if not sacs:
            return cost
        return max(0, (d.cost if cost is None else cost) - sum(self.chars(c)["sac_reduce"] for c in sacs))

    def _tap_pool(self, p) -> list[int]:
        return [c for c in self.bz_tops(p) if "creature" in self.chars(c)["types"] and not self.s.cards[c].tapped]

    def _tap_reduced(self, d, p, cost, tapped):
        """ハイパーエナジー: タップしたクリーチャー1体につきコストを減らす（床は0）。tapped=None は最大限タップした場合。"""
        if not d.tap_reduce:
            return cost
        n = len({self.chars(c)["cost"] for c in self._tap_pool(p)}) if tapped is None else len(tapped)
        return max(0, (d.cost if cost is None else cost) - n * d.tap_reduce)

    def _evo_sources(self, cid, p, face=None) -> list[int]:
        """適正な進化元（801.1a）。evolve_zone（既定は自分のバトルゾーン）のクリーチャーで
        evolve_from を満たすもの（超無限墓地進化は自分の墓地から選ぶ）。"""
        f = self.cdef(cid).face(face)
        ef = {k: v for k, v in (f.evolve_from or {}).items() if k != "zone"} or {}
        z = f.evolve_zone
        pool = self.bz_tops(p) if z == "bz" else self.zlist(z, p)
        return [c for c in pool if ("creature" in self.chars(c)["types"] or self.permits(c, "evolve_base"))
                and self.filter_match(c, ef)]

    def _mana_choices(self, cid, p, face=None, cost: int | None = None, limit: int = 32) -> list[list[int]]:
        """支払いに使うマナの組（112.2a）。文明は1文明につき別々の1枚で満たし、マナの数値の合計がコストに一致。
        cost: 実行時に確定したコスト（進化元数の軽減など）。指定なければカード定義のコスト。"""
        d = self.cdef(cid).face(face)
        eff = d.cost if cost is None else cost
        ch = self.chars(cid, face)
        eff = max(0, eff + ch["pay_cost"] - d.cost)           # 継続的効果によるコストの増減（mod cost）
        if eff == 0 and not d.civs:
            return [[]]
        untapped = [c for c in self.zlist("mana", p) if not self.s.cards[c].tapped]
        if len(untapped) < len(d.civs) or sum(self.cdef(c).mana for c in untapped) < eff:
            return []
        groups: dict[str, list[int]] = {}
        for c in untapped:
            groups.setdefault(self.s.cards[c].defn, []).append(c)
        names = sorted(groups)
        need = list(d.civs)
        mana = [self.rules.cards[n].mana for n in names]
        out: list[list[int]] = []

        def civ_ok(cnt):
            civsets = [set(self.rules.cards[n].civs) for n, k in zip(names, cnt) for _ in range(k)]
            return any(all(need[j] in civsets[perm[j]] for j in range(len(need)))
                       for perm in itertools.permutations(range(len(civsets)), len(need)))

        def dfs(i, cnt, total, zeros):
            if len(out) >= limit:
                return
            if i == len(names):
                if total == eff and civ_ok(cnt):
                    out.append([c for n, k in zip(names, cnt) for c in groups[n][:k]])
                return
            cap = len(groups[names[i]])
            for k in range(min(cap, (eff - total) // mana[i] if mana[i] else len(need) - zeros), -1, -1):
                dfs(i + 1, cnt + [k], total + k * mana[i], zeros + (0 if mana[i] else k))

        def floor_dfs(i, cnt, left):
            """112.2b: コストが文明の数を下回ったら文明の支払いを優先する（マナの数値の合計は問わない）。"""
            if len(out) >= limit:
                return
            if i == len(names):
                if left == 0 and civ_ok(cnt):
                    out.append([c for n, k in zip(names, cnt) for c in groups[n][:k]])
                return
            for k in range(min(len(groups[names[i]]), left), -1, -1):
                floor_dfs(i + 1, cnt + [k], left - k)

        if eff < len(need):
            floor_dfs(0, [], len(need))
        else:
            dfs(0, [], 0, 0)
        return out

    def play_task(self, cid, p, free, face=None, st=False) -> dict:
        t = {"t": "play", "cid": cid, "player": p, "free": free, "phase": "start", "gen": self.s.cards[cid].gen}
        if face is not None:
            t["face"] = face
        if st:
            t["st"] = True
        return t


@task("turn", TurnTask)
def h_turn(eng, t):
    s = eng.s
    if s.skip_rest:          # 「ターンの残りをとばす」: 残りのステップを行わずに次のターンへ（ターン終了時の誘発もなし）
        s.skip_rest = False
        t["i"] = len(t["steps"])
        eng._expire("end_of_turn")
        return None          # 状況起因処理と待機中の効果を、このターンのうちに済ませる
    if t["i"] < len(t["steps"]):
        name = t["steps"][t["i"]]
        s.step = name
        return STEPS[name](eng, t)
    # 512 次のターンへ
    for c in list(s.hold):                              # 512.1 保留状態のカードは墓地へ（誘発なし）
        eng._raw_move(c, "graveyard")
    s.active = s.extra_turns.pop(0) if s.extra_turns else 1 - s.active   # 500.5
    s.turn += 1
    if s.turn > eng.turn_limit:
        s.result = {"winner": None, "reason": "turn_limit", "turn": s.turn}
    t.update(steps=eng._build_steps(s.active), i=0, sub=0)
    return None


@step("start")
def st_start(eng, t):                                   # 501
    s = eng.s
    a = s.active
    s.steps_this_turn = 0
    s.turn_counters = {}
    n = len(s.continuous)
    s.continuous = [c for c in s.continuous if c["duration"] != f"until_turn_start:{a}"]
    s.delayed = [d for d in s.delayed if d["duration"] != f"until_turn_start:{a}"]
    untap = [{"ev": "untap", "subject": s.ref(c)}
             for c in eng.bz_tops(a) + eng.zlist("mana", a)
             if s.cards[c].tapped and eng.permits(c, "untap_at_start")]
    eng._step_done(t)
    # ターン起因処理（同時にアンタップ, 702.3a）→「ターンのはじめに」の誘発（501.2）
    eng._push(*([eng.ev_task(untap)] if untap else []), eng.ev_task({"ev": "turn_start", "player": a}))
    if len(s.continuous) != n:
        eng._sba()           # 期限切れでパワー0以下になったものを先に破壊（703.1）


@step("draw")
def st_draw(eng, t):                                    # 502
    s = eng.s
    eng._step_done(t)
    if not (s.turn == 1 and s.active == s.first_player):   # 500.6
        eng._push(eng.ev_task({"ev": "draw", "player": s.active}))


@step("charge")
def st_charge(eng, t):                                  # 503
    s = eng.s
    a = s.active
    opts = eng._distinct_hand_options(a, "charge") + [{"key": "pass"}]
    ans, d = eng.ask(t, a, "charge", opts)
    if d:
        return d
    eng._step_done(t)
    o = opts[ans[0]]
    if o["key"] != "pass":
        eng._push(eng.ev_task({"ev": "move", "subject": s.ref(o["cid"]), "to": "mana", "reason": "charge"}))


@step("main")
def st_main(eng, t):                                    # 504
    a = eng.s.active
    opts = eng._play_options(a) + eng._cross_options(a) + [{"key": "pass"}]
    ans, d = eng.ask(t, a, "main", opts)
    if d:
        return d
    o = opts[ans[0]]
    if o["key"] == "pass":
        eng._step_done(t)
    elif o["key"].startswith("cross:"):
        eng._push({"t": "cross", "gear": eng.s.ref(o["cid"]), "target": o["target"], "player": a})
    else:
        eng._push(eng.play_task(o["cid"], a, o.get("free", False), o.get("face")))


@step("attack")
def st_attack(eng, t):                                  # 505
    s = eng.s
    a = s.active
    atk = eng._attack_options(a)
    forced = {o["cid"] for o in atk if "attack" in eng.chars(o["cid"])["require"]}   # 506.1b 攻撃を強制されたクリーチャーは攻撃させなくてはいけない
    act = [o for o in eng._activate_options(a, atk) if o["tap"] not in forced]       # タップ能力で攻撃を免れることはできない
    opts = atk + act + ([] if forced else [{"key": "pass"}])
    ans, d = eng.ask(t, a, "attack", opts)
    if d:
        return d
    o = opts[ans[0]]
    if o["key"] == "pass":
        eng._step_done(t)
    elif o["key"].startswith("activate:"):                  # 602 起動型能力: コスト（タップ）を払い、効果は待機状態になる
        s.cards[o["tap"]].tapped = True
        ab = dict(eng.abilities(o["cid"], "activate"))[o["ab"]]
        eng._push(eng._child(ab["effect"], {"you": a, "self": s.ref(o["cid"]), "vars": {}}))
    else:
        eng._push({"t": "attack", "attacker": s.ref(o["cid"]), "target": o["target"], "phase": 0, "cp": True})


@step("end")
def st_end(eng, t):                                     # 511
    if t["sub"] == 0:
        t["sub"] = 1
        eng._push(eng.ev_task({"ev": "turn_end", "player": eng.s.active}))
        return None
    eng._expire("end_of_turn")                          # 511.2
    eng._step_done(t)


@task("cross", CrossTask)
def h_cross(eng, t):
    """クロスする（303.3, 701.17）。マナコストをもう一度支払い、クロスギアをクリーチャーに付ける。"""
    s = eng.s
    g, tg, p = t["gear"], t["target"], t["player"]
    if not (s.alive(g) and s.alive(tg)) or s.cards[g[0]].zone != "bz" or s.cards[tg[0]].zone != "bz":
        eng._pop(t)
        return None
    choices = eng._mana_choices(g[0], p)
    if not choices:
        eng._pop(t)
        return None
    opts = [{"key": "mana:" + ",".join(sorted(s.cards[c].defn for c in ch)), "cids": ch} for ch in choices]
    ans, dd = eng.ask(t, p, "pay_mana", opts)
    if dd:
        return dd
    for c in opts[ans[0]]["cids"]:
        s.cards[c].tapped = True
    s.cards[g[0]].crossed = list(tg)
    eng._pop(t)
    return None


@task("play", PlayTask)
def h_play(eng, t):
    """カードの実行（601）。free=True はコストを支払わずに実行（S・トリガー等）。それでも召喚・詠唱したことになる（112.3g）。
    ツインパクトは face で実行する面を選ぶ（810.3）。進化は進化元を選んでその上に重ねる（801）。"""
    s = eng.s
    cid, p = t["cid"], t["player"]
    face = t.get("face")
    if s.cards[cid].gen != t["gen"] or s.cards[cid].zone in ("bz", "hold"):
        eng._pop(t)
        return None
    d = eng.cdef(cid).face(face)
    action = "summon" if d.is_creature() else "generate" if d.is_permanent() else "cast"
    if not eng.permits(cid, action) or (d.is_creature() and not eng.permits(cid, "enter_bz")):
        eng._pop(t)
        return None
    if "evolution" in d.types and "evo" not in t:
        srcs = eng._evo_sources(cid, p, face)
        if not srcs:
            eng._pop(t)
            return None
        opts = [eng._card_option(c) for c in srcs]
        mn, mx = (1, len(srcs)) if d.evolve_any else (1, 1)
        ans, dd = eng.ask(t, p, "choose_evo_source", opts, mn, mx)
        if dd:
            return dd
        t["evo"] = [s.ref(srcs[i]) for i in ans]
    if d.tap_reduce and not t["free"] and not t.get("tap_done"):     # ハイパーエナジー: コストが異なるクリーチャーを好きな数タップ
        chosen = t.setdefault("tap", [])
        used = {eng.chars(c)["cost"] for c in chosen}
        cands = [c for c in eng._tap_pool(p) if c not in chosen and eng.chars(c)["cost"] not in used]
        if cands:
            ans, dd = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in cands], 0, 1)
            if dd:
                return dd
            if ans:
                chosen.append(cands[ans[0]])
                return None
        t["tap_done"] = True
    if not t["free"] and not t.get("sac_done"):                      # ササゲール: 破壊するクリーチャーを任意に選ぶ
        chosen = t.setdefault("sac", [])
        cands = [c for c in eng._sac_pool(d, p) if c not in chosen]
        if cands:
            ans, dd = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in cands], 0, 1)
            if dd:
                return dd
            if ans:
                chosen.append(cands[ans[0]])
                return None
        t["sac_done"] = True
    ch0 = eng.chars(cid, face)
    if ch0["opt_reduce"] and not t["free"] and not t.get("reduce_done"):    # B・A・D / J・O・E: 減らして実行するか選ぶ
        ans, dd = eng.ask(t, p, "choose_cards", [{"key": "reduce"}, {"key": "normal"}], 1, 1)
        if dd:
            return dd
        t["reduced"] = ans[0] == 0
        t["reduce_done"] = True
    if not t["free"]:
        n = len(t.get("evo", []))
        cost = max(0, d.cost - n * d.cost_reduce_per_evo) if d.cost_reduce_per_evo else None
        cost = eng._sac_reduced(d, eng._tap_reduced(d, p, cost, t.get("tap", [])), t.get("sac", []))
        if t.get("reduced"):
            cost = max(0, (d.cost if cost is None else cost) - ch0["opt_reduce"]["amount"])
        choices = eng._mana_choices(cid, p, face, cost=cost)
        if not choices:
            eng._pop(t)
            return None
        opts = [{"key": "mana:" + ",".join(sorted(s.cards[c].defn for c in ch)), "cids": ch} for ch in choices]
        ans, dd = eng.ask(t, p, "pay_mana", opts)
        if dd:
            return dd
        for c in opts[ans[0]]["cids"] + t.get("tap", []):
            s.cards[c].tapped = True
    eng._pop(t)
    from_zone = s.cards[cid].zone
    eng._to_hold(cid)
    if face is not None:
        s.cards[cid].face = face
    ref = s.ref(cid)
    if d.is_creature():
        ev = {"ev": "move", "subject": ref, "from": from_zone, "to": "bz", "reason": "summon", "controller": p,
              "unpaid": bool(t["free"])}
        if t.get("evo"):
            ev["stack_on"] = t["evo"][0]
            if len(t["evo"]) > 1:
                ev["stack_more"] = t["evo"][1:]
        eng._push(eng.ev_task(ev))
    elif d.is_permanent():      # タマシード・フィールド・クロスギア: 実行（展開・ジェネレート）したらバトルゾーンに出る（315.2, 308.2, 303.2）
        eng._push(eng.ev_task({"ev": "move", "subject": ref, "from": from_zone, "to": "bz", "reason": "put",
                               "controller": p, "via": "generate", "unpaid": bool(t["free"])}))
    else:   # 呪文: 唱えた → 書かれた順に解決 → 最終段階として墓地へ（605.2f）
        env = {"you": p, "self": ref, "vars": {}}
        if t.get("st"):
            env["in_st"] = True
        eng._push(eng.ev_task({"ev": "cast", "player": p, "subject": ref, "unpaid": bool(t["free"])}),
                   eng._child(d.spell, env),
                   eng.ev_task({"ev": "move", "subject": ref, "from": from_zone, "to": t.get("resolve_to", d.resolve_to),
                                 "reason": "resolve", "position": t.get("resolve_position", "top")}),
                   *([eng._child(d.after_resolve, env)] if d.after_resolve else []))
    if t.get("reduced"):   # 減らして実行したら、そのターンの終わりに処理する。実行の解決より後に積む＝先に処理する
        then = ch0["opt_reduce"]["then"]
        end = [{"op": "move", "select": {"ref": "self_entered"}, "to": "graveyard", "reason": "destroy"}] if then == "destroy" else \
              [{"op": "move", "select": {"ref": "self_entered"}, "to": "deck", "reason": "put", "position": "bottom"},
               {"op": "draw", "count": 1}]
        eng._push(eng._child([{"op": "delayed_trigger", "when": {"event": "turn_end"}, "effect": end}],
                             {"you": p, "self": ref, "vars": {}}))
    if t.get("sac"):       # ササゲール: 軽減したら破壊する（支払いの一部。実行の解決より先に行う）
        eng._push(eng.ev_task([{"ev": "move", "subject": s.ref(c), "to": "graveyard", "reason": "destroy"}
                               for c in t["sac"]]))
    return None
