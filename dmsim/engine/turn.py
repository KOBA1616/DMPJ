"""ターン構造（500〜512）、カードの実行（601）、マナ支払い（112.2a）。

ターンはステップの列（data/rules/turn.yaml）で、各ステップの処理は @step で登録する。
ターンが始まる時に state.step_mods（効果による「飛ばす」「もう一度行う」）を反映した列を作る。
"""
from __future__ import annotations

import itertools

from ..types import CrossTask, HyperTask, PlayTask, TurnTask
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
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                if f.neo and f.evolve_from and self._evo_sources(cid, p, fi):   # NEO進化: 重ねて出す選択肢
                    opt = {"key": f"{o['key']}:neo" if fi is None else f"{o['key']}:{fi}:neo", "cid": cid,
                           "name": f.name, "neo": True}
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                gs = f.galaxy_shield   # ギャラクシールド: 代替コストで表向きにシールド化する選択肢
                if gs and self._mana_choices(cid, p, fi, cost=gs["cost"], limit=1, civs=gs["civs"]):
                    opt = {"key": f"{o['key']}:gshield" if fi is None else f"{o['key']}:{fi}:gshield", "cid": cid,
                           "name": f.name, "gshield": True}
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                mc = f.mugen_climb   # ムゲンクライム: 自分のクリーチャーをタップし代替コストを払って手札/墓地から実行
                if mc and self._climb_ready(cid, p, fi, mc):
                    opt = {"key": f"{o['key']}:climb" if fi is None else f"{o['key']}:{fi}:climb", "cid": cid,
                           "name": f.name, "climb": True}
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
        seen_mc = set()   # ムゲンクライム: 墓地からも実行できる
        for cid in self.zlist("graveyard", p):
            dn = self.s.cards[cid].defn
            if dn in seen_mc:
                continue
            d = self.cdef(cid)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                mc = f.mugen_climb
                if mc and self._climb_ready(cid, p, fi, mc):
                    seen_mc.add(dn)
                    opt = {"key": f"play:{dn}:climb" if fi is None else f"play:{dn}:{fi}:climb",
                           "cid": cid, "name": f.name, "climb": True}
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
        seen = set()   # アビスラッシュ: 墓地から召喚できるカードも選択肢に出す
        for cid in self.zlist("graveyard", p):
            dn = self.s.cards[cid].defn
            if dn in seen or not self.permits(cid, "summon_from_graveyard"):
                continue
            seen.add(dn)
            d = self.cdef(cid)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                if self._can_play_face(cid, p, fi):
                    opt = {"key": f"play:{dn}:rush" if fi is None else f"play:{dn}:{fi}:rush",
                           "cid": cid, "name": f.name, "rush": True}
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
        return out

    def _climb_ready(self, cid, p, fi, mc) -> bool:
        """ムゲンクライムの前提: 代替コストが払えて、タップできる自分のクリーチャーが足りる。"""
        f = self.cdef(cid).face(fi)
        action = "summon" if f.is_creature() else "generate" if f.is_permanent() else "cast"
        if not self.permits(cid, action):
            return False
        pool = [c for c in self.bz_tops(p) if not self.s.cards[c].tapped
                and "creature" in self.chars(c)["types"]]
        return len(pool) >= mc["tap"] and bool(self._mana_choices(cid, p, fi, cost=mc["cost"], limit=1, civs=mc["civs"]))

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

    def _hyper_options(self, p: int) -> list[dict]:
        """ハイパー化: ハイパーモードでない自分のクリーチャーで、タップできる他の自分のクリーチャーがいるもの。"""
        s = self.s
        out = []
        allies = [c for c in self.bz_tops(p) if not s.cards[c].tapped]
        for c in self.bz_tops(p):
            if self.is_hyper(c) or not self.fdef(c).hyper:
                continue
            if any(a != c for a in allies):
                out.append({"key": f"hyper:{s.cards[c].defn}", "cid": c, "hyper_act": True})
        return out

    def _can_play_face(self, cid, p, face) -> bool:
        d = self.cdef(cid).face(face)
        action = "summon" if d.is_creature() else "generate" if d.is_permanent() else "cast"
        if not self.permits(cid, action) or (d.is_creature() and not self.permits(cid, "enter_bz")):
            return False
        if "evolution" in d.types:
            srcs = self._evo_sources(cid, p, face)
            if len(srcs) < d.evolve_count:
                return False
            n = len(srcs) if d.evolve_any else d.evolve_count           # 最も安い組合せで払えるか（112.2b）
            cost = max(0, d.cost - n * d.cost_reduce_per_evo) if d.cost_reduce_per_evo else None
            return bool(self._mana_choices(cid, p, face, cost=self._opt_reduced(cid, face, d, self._sac_reduced(d, self._tap_reduced(d, p, cost, None), self._sac_pool(d, p))), limit=1))
        return bool(self._mana_choices(cid, p, face, cost=self._opt_reduced(cid, face, d, self._sac_reduced(d, self._tap_reduced(d, p, None, None), self._sac_pool(d, p))), limit=1))

    def _opt_reduced(self, cid, face, d, cost):
        """任意の軽減（opt_reduce / cost_may）をすべて使った場合の最安コスト（実行可能かの判定用）。"""
        base = d.cost if cost is None else cost
        o = self.chars(cid, face)["opt_reduce"]
        if o:
            n = 1
            if o.get("do") and o.get("per"):   # 支払い時の行動1件につき軽減: 選べる最大数で見積もる
                env = {"you": self.s.cards[cid].controller, "self": self.s.ref(cid)}
                n = min(o["do"].get("max", 99), len([c for c in self.candidates(o["do"]["select"], env) if c != cid]))
            base = max(o.get("floor", 0), base - o["amount"] * n)
        cm = self._cost_may_avail(cid, face)
        if cm:
            base = max(max(e.get("min", 0) for e in cm), base - sum(e["amount"] for e in cm))
        return base if (o or cm) else cost

    def _opt_amount(self, o, fuel) -> int:
        """実際に得る軽減量: per なら支払い時の行動の件数 × amount。"""
        return o["amount"] * (len(fuel) if o.get("per") else 1)

    def _cost_may_avail(self, cid, face=None) -> list[dict]:
        """今使える任意のコスト軽減（mod cost_may）。once のものは発生源ごとにターン中1回まで。"""
        out = []
        for e in self.chars(cid, face)["cost_may"]:
            if e.get("once") and self.s.turn_counters.get(f"cost_may:{e['src']}"):
                continue
            out.append(e)
        return out

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

    def _mana_choices(self, cid, p, face=None, cost: int | None = None, limit: int = 32, civs=None) -> list[list[int]]:
        """支払いに使うマナの組（112.2a）。文明は1文明につき別々の1枚で満たし、マナの数値の合計がコストに一致。
        cost: 実行時に確定したコスト（進化元数の軽減など）。指定なければカード定義のコスト。
        civs: 必要な文明の上書き（代替コスト用）。"""
        d = self.cdef(cid).face(face)
        eff = d.cost if cost is None else cost
        ch = self.chars(cid, face)
        eff = max(0, eff + ch["pay_cost"] - d.cost)           # 継続的効果によるコストの増減（mod cost）
        if eff == 0 and not (civs if civs is not None else d.civs):
            return [[]]
        untapped = [c for c in self.zlist("mana", p) if not self.s.cards[c].tapped]
        if len(untapped) < len(d.civs) or sum(self.cdef(c).mana for c in untapped) < eff:
            return []
        groups: dict = {}
        for c in untapped:   # 裏向きマナは無色として別グループに分ける（水晶武装）
            groups.setdefault((self.s.cards[c].defn, self.s.cards[c].face_down), []).append(c)
        names = sorted(groups)
        need = list(civs) if civs is not None else list(d.civs)
        mana = [self.rules.cards[n[0]].mana for n in names]
        out: list[list[int]] = []

        def civ_ok(cnt):
            civsets = [set() if n[1] else set(self.rules.cards[n[0]].civs) for n, k in zip(names, cnt) for _ in range(k)]
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
    for c in eng.zlist("bz", s.active):                 # ハイパーモードは次の自分のターンのはじめまで（文字通り。相手ターンに解放されても自分のターンのはじめに戻る）
        s.cards[c].hyper = False
    a = s.active
    s.steps_this_turn = 0
    s.turn_counters = {}
    n = len(s.continuous)
    s.continuous = [c for c in s.continuous if c["duration"] != f"until_turn_start:{a}"]
    s.delayed = [d for d in s.delayed if d["duration"] != f"until_turn_start:{a}"]
    cands = [c for c in eng.bz_tops(a) if s.cards[c].tapped and eng.permits(c, "untap_at_start") and eng.abilities(c, "silent")]
    skill = []
    if cands:                          # 501.1a サイレントスキル: アンタップしないことを選び、かわりに能力を使ってもよい
        ans, d = eng.ask(t, a, "choose_cards", [eng._card_option(c) for c in cands], 0, len(cands))
        if d:
            return d
        skill = [cands[i] for i in ans]
    frozen = [c for c in eng.bz_tops(a) + eng.zlist("mana", a) if s.cards[c].no_untap_next]
    for c in frozen:                       # フリーズ等: 印を消費してこの回のアンタップをしない
        s.cards[c].no_untap_next = False
    untap = [{"ev": "untap", "subject": s.ref(c)}
             for c in eng.bz_tops(a) + eng.zlist("mana", a)
             if s.cards[c].tapped and eng.permits(c, "untap_at_start") and c not in skill and c not in frozen]
    eng._step_done(t)
    # ターン起因処理（同時にアンタップ, 702.3a）→ サイレントスキルの解決（他のカードのアンタップの後, 501.1a）→「ターンのはじめに」の誘発（501.2）
    effects = [eng._child(ab["effect"], {"you": a, "self": s.ref(c), "vars": {}}) for c in skill for _, ab in eng.abilities(c, "silent")]
    eng._push(*([eng.ev_task(untap)] if untap else []), *effects, eng.ev_task({"ev": "turn_start", "player": a}))
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
    opts = eng._play_options(a) + eng._cross_options(a) + eng._hyper_options(a) + [{"key": "pass"}]
    ans, d = eng.ask(t, a, "main", opts)
    if d:
        return d
    o = opts[ans[0]]
    if o["key"] == "pass":
        eng._step_done(t)
    elif o.get("hyper_act"):
        eng._push({"t": "hyper", "cid": o["cid"], "player": a})
    elif o["key"].startswith("cross:"):
        eng._push({"t": "cross", "gear": eng.s.ref(o["cid"]), "target": o["target"], "player": a})
    else:
        task = eng.play_task(o["cid"], a, o.get("free", False), o.get("face"))
        if o.get("rush"):
            task["rush"] = True
        if o.get("gshield"):
            fd = eng.cdef(o["cid"]).face(o.get("face"))
            task["to_shield"] = True
            task["cost_override"] = fd.galaxy_shield["cost"]
            task["cost_civs"] = fd.galaxy_shield["civs"]
        if o.get("climb"):
            fd = eng.cdef(o["cid"]).face(o.get("face"))
            task["climb"] = True
            task["cost_override"] = fd.mugen_climb["cost"]
            task["cost_civs"] = fd.mugen_climb["civs"]
        if o.get("neo"):
            task["evo_mode"] = True
        eng._push(task)


@task("hyper", HyperTask)
def h_hyper(eng, t):
    """ハイパーモードの解放: 自分の他のクリーチャーを1体タップし、このクリーチャーをハイパーモードにする。"""
    s = eng.s
    cid, p = t["cid"], t["player"]
    c = s.cards[cid]
    if c.zone != "bz" or eng.is_hyper(cid):
        eng._pop(t)
        return None
    cands = [x for x in eng.bz_tops(p) if x != cid and not s.cards[x].tapped]
    if not cands:
        eng._pop(t)
        return None
    ans, d = eng.ask(t, p, "choose_cards", [eng._card_option(x) for x in cands], 1, 1)
    if d:
        return d
    target = cands[ans[0]]
    c.hyper = True
    eng._pop(t)
    eng._push(eng.ev_task([{"ev": "tap", "subject": s.ref(target)}]))
    return None


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
    # スーパー・S・トリガー: シールドが1つもない時に使ったら追加能力を得る（印は移動後に付ける）
    sst_bonus = bool(t.get("st") and "super_s_trigger" in eng.chars(cid, face)["keywords"]
                     and not eng.zlist("shield", p))
    # S・トリガー・プラス: 相手のターンで、そのターンに自分のシールドが2つ以上ブレイクされていれば追加能力を得る
    stp_bonus = bool(t.get("st") and "s_trigger_plus" in eng.chars(cid, face)["keywords"]
                     and s.active != p and s.turn_counters.get(f"broken:{p}", 0) >= 2)
    if ("evolution" in d.types or t.get("evo_mode")) and "evo" not in t:
        srcs = eng._evo_sources(cid, p, face)
        if len(srcs) < d.evolve_count:
            eng._pop(t)
            return None
        opts = [eng._card_option(c) for c in srcs]
        mn, mx = (1, len(srcs)) if d.evolve_any else (d.evolve_count, d.evolve_count)
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
    if t.get("climb") and not t.get("climb_done"):   # ムゲンクライム: 自分のクリーチャーを指定数タップする
        mc = d.mugen_climb
        pool = [c for c in eng.bz_tops(p) if not s.cards[c].tapped and "creature" in eng.chars(c)["types"]]
        if len(pool) < mc["tap"]:
            eng._pop(t)
            return None
        ans, dd = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in pool], mc["tap"], mc["tap"])
        if dd:
            return dd
        for i in ans:
            s.cards[pool[i]].tapped = True
        t["climb_done"] = True
    ch0 = eng.chars(cid, face)
    flag = f"last_play_creature:{p}"
    cyc = "cyclone" in ch0["keywords"] and bool(s.turn_counters.get(flag))   # サイクロン: 唱える直前に召喚していたか（直前の実行が召喚）
    s.turn_counters[flag] = int(d.is_creature())
    if ch0["opt_reduce"] and not t["free"] and not t.get("reduce_done"):    # B・A・D / J・O・E: 減らして実行するか選ぶ
        ans, dd = eng.ask(t, p, "choose_cards", [{"key": "reduce"}, {"key": "normal"}], 1, 1)
        if dd:
            return dd
        t["reduced"] = ans[0] == 0
        t["reduce_done"] = True
    if t.get("reduced") and ch0["opt_reduce"].get("do") and not t.get("fuel_done"):
        # 支払い時の行動（手札を見せる・捨てる、シールドを手札に加える、墓地の呪文を山札に戻す等）を先に行う
        spec = ch0["opt_reduce"]["do"]
        env = {"you": p, "self": s.ref(cid)}
        cands = [c for c in eng.candidates(spec["select"], env) if c != cid]   # 実行中のカード自身は対象にしない
        mx = min(spec.get("max", len(cands)), len(cands))
        if mx <= 0:
            t["reduced"] = False          # 行動できないなら軽減も得られない
            t["fuel_done"] = True
        else:
            ans, dd = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in cands],
                              min(spec.get("min", 0), mx), mx)
            if dd:
                return dd
            t["fuel"] = [cands[i] for i in ans]
            t["fuel_done"] = True
            if spec.get("tap"):   # 燃料としてタップする（コストの支払い。ゾーンは動かない）
                for c in t["fuel"]:
                    s.cards[c].tapped = True
            if spec.get("move_to"):
                reason = {"graveyard": "discard", "hand": "return", "deck": "put"}.get(spec["move_to"], "put")
                seq = [eng.ev_task([{"ev": "move", "subject": s.ref(c), "to": spec["move_to"],
                                     "reason": reason} for c in t["fuel"]])]
                if spec.get("shuffle"):
                    seq.append(eng._child([{"op": "shuffle"}], {"you": p, "self": s.ref(cid), "vars": {}}))
                eng._push(*seq)
                return None               # 行動の適用を終えてから支払いに進む
    if not t["free"] and not t.get("cost_may_done"):    # 任意のコスト軽減（cost_may）: 発生源ごとに使うか選ぶ
        avail = eng._cost_may_avail(cid, face)
        i = t.get("cost_may_i", 0)
        while i < len(avail):
            e = avail[i]
            ans, dd = eng.ask(t, p, "choose_cards", [{"key": "reduce"}, {"key": "normal"}], 1, 1)
            if dd:
                t["cost_may_i"] = i
                return dd
            if ans[0] == 0:
                t["cost_may_total"] = t.get("cost_may_total", 0) + e["amount"]
                t["cost_may_min"] = max(t.get("cost_may_min", 0), e.get("min", 0))
                if e.get("once"):
                    s.turn_counters[f"cost_may:{e['src']}"] = 1
            i += 1
        t["cost_may_done"] = True
    if not t["free"] and not t.get("paid_done"):
        n = len(t.get("evo", []))
        cost = max(0, d.cost - n * d.cost_reduce_per_evo) if d.cost_reduce_per_evo else None
        cost = eng._sac_reduced(d, eng._tap_reduced(d, p, cost, t.get("tap", [])), t.get("sac", []))
        if t.get("reduced"):
            o = ch0["opt_reduce"]
            cost = max(o.get("floor", 0), (d.cost if cost is None else cost) - eng._opt_amount(o, t.get("fuel", [])))
        if t.get("cost_may_total"):
            cost = max(t.get("cost_may_min", 0), (d.cost if cost is None else cost) - t["cost_may_total"])
        if t.get("cost_override") is not None:   # 代替コスト（キリフダッシュ等）は他の軽減より優先して総額を置き換える
            cost = t["cost_override"]
        choices = eng._mana_choices(cid, p, face, cost=cost, civs=t.get("cost_civs"))
        if not choices:
            eng._pop(t)
            return None
        opts = [{"key": "mana:" + ",".join(sorted(s.cards[c].defn for c in ch)), "cids": ch} for ch in choices]
        ans, dd = eng.ask(t, p, "pay_mana", opts)
        if dd:
            return dd
        for c in opts[ans[0]]["cids"] + t.get("tap", []):
            s.cards[c].tapped = True
        t["paid_done"] = True   # 後段（バズレンダ等）の決定で再入しても二重に支払わない
    if d.bazurenda and not t["free"]:   # バズレンダ: 追加でこのコストを好きな回数支払ってもよい
        while not t.get("bz_done"):
            cnt = t.get("bz_count", 0)
            if t.get("bz_yn_for") != cnt:
                ans, dd = eng.ask(t, p, "yes_no", [{"key": "yes"}, {"key": "no"}], prompt="バズレンダ: 追加で支払う")
                if dd:
                    return dd
                t["bz_yn_for"] = cnt
                t["bz_pay"] = ans[0] == 0
            if not t["bz_pay"]:
                t["bz_done"] = True
                break
            if t.get("bz_paid_for") != cnt:
                choices = eng._mana_choices(cid, p, face, cost=d.bazurenda["cost"],
                                            civs=d.bazurenda.get("civs") or None)
                if not choices:
                    t["bz_done"] = True
                    break
                opts = [{"key": "mana:" + ",".join(sorted(s.cards[c].defn for c in ch)), "cids": ch} for ch in choices]
                ans, dd = eng.ask(t, p, "pay_mana", opts)
                if dd:
                    return dd
                for c in opts[ans[0]]["cids"]:
                    s.cards[c].tapped = True
                t["bz_paid_for"] = cnt
            t["bz_count"] = cnt + 1
    if d.o_drive and not t["free"] and not t.get("od_done"):   # O・ドライブ: 追加で指定文明のマナをタップしてもよい
        if t.get("od_yn") is None:
            pool = [c for c in eng.zlist("mana", p) if not s.cards[c].tapped
                    and d.o_drive["civ"] in eng.chars(c)["civs"]]
            if len(pool) < d.o_drive["count"]:
                t["od_yn"] = False
            else:
                ans, dd = eng.ask(t, p, "yes_no", [{"key": "yes"}, {"key": "no"}], prompt="O・ドライブ: 追加でタップする")
                if dd:
                    return dd
                t["od_yn"] = ans[0] == 0
        if t.get("od_yn"):
            pool = [c for c in eng.zlist("mana", p) if not s.cards[c].tapped
                    and d.o_drive["civ"] in eng.chars(c)["civs"]]
            ans, dd = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in pool],
                              d.o_drive["count"], d.o_drive["count"])
            if dd:
                return dd
            for i in ans:
                s.cards[pool[i]].tapped = True
            t["odrive"] = True
        t["od_done"] = True
    eng._pop(t)
    from_zone = s.cards[cid].zone
    eng._to_hold(cid)
    if sst_bonus:
        s.cards[cid].sst = True
    if stp_bonus:
        s.cards[cid].stp = True
    if d.bazurenda:
        s.cards[cid].bazurenda = t.get("bz_count", 0)
    if face is not None:
        s.cards[cid].face = face
    ref = s.ref(cid)
    if t.get("to_shield"):   # ギャラクシールド: 代替コストを払って表向きにシールド化する（召喚ではない）
        eng._push(eng.ev_task({"ev": "move", "subject": ref, "from": from_zone, "to": "shield", "reason": "put",
                               "controller": p, "face_up": True}))
        return None
    if d.is_creature():
        ev = {"ev": "move", "subject": ref, "from": from_zone, "to": "bz", "reason": "summon", "controller": p,
              "unpaid": bool(t["free"]) and not t.get("as_paid")}
        if sst_bonus:
            ev["sst"] = True
        if stp_bonus:
            ev["stp"] = True
        if t.get("odrive"):
            ev["odrive"] = True
        if d.bazurenda:
            ev["bazurenda"] = t.get("bz_count", 0)
        if t.get("evo"):
            ev["stack_on"] = t["evo"][0]
            if len(t["evo"]) > 1:
                ev["stack_more"] = t["evo"][1:]
        eng._push(eng.ev_task(ev))
    elif d.is_permanent():      # タマシード・フィールド・クロスギア: 実行（展開・ジェネレート）したらバトルゾーンに出る（315.2, 308.2, 303.2）
        ev = {"ev": "move", "subject": ref, "from": from_zone, "to": "bz", "reason": "put",
              "controller": p, "via": "generate", "unpaid": bool(t["free"])}
        if sst_bonus:
            ev["sst"] = True
        if d.bazurenda:
            ev["bazurenda"] = t.get("bz_count", 0)
        eng._push(eng.ev_task(ev))
    else:   # 呪文: 唱えた → 書かれた順に解決 → 最終段階として墓地へ（605.2f）
        env = {"you": p, "self": ref, "vars": {}}
        if t.get("st"):
            env["in_st"] = True
        spell_ops = list(d.spell) + (list(d.sst_spell) if s.cards[cid].sst else []) \
            + (list(d.stp_spell) if s.cards[cid].stp else [])
        reps = 1 + (s.cards[cid].bazurenda if d.bazurenda else 0)   # バズレンダ呪文は能力を1+追加回数使う
        eng._push(eng.ev_task({"ev": "cast", "player": p, "subject": ref, "unpaid": bool(t["free"])}),
                   *([eng._child(spell_ops, env)] * reps),
                   eng.ev_task({"ev": "move", "subject": ref, "from": from_zone, "to": t.get("resolve_to", "hand" if cyc else d.resolve_to),
                                 "reason": "resolve", "position": t.get("resolve_position", "top")}),
                   *([eng._child(d.after_resolve, env)] if d.after_resolve else []))
    if t.get("reduced") and ch0["opt_reduce"].get("then"):   # 減らして実行したら、そのターンの終わりに処理する。実行の解決より後に積む＝先に処理する
        then = ch0["opt_reduce"]["then"]
        end = [{"op": "move", "select": {"ref": "self_entered"}, "to": "graveyard", "reason": "destroy"}] if then == "destroy" else \
              [{"op": "move", "select": {"ref": "self_entered"}, "to": "deck", "reason": "put", "position": "bottom"},
               {"op": "draw", "count": 1}]
        eng._push(eng._child([{"op": "delayed_trigger", "when": {"event": "turn_end"}, "effect": end}],
                             {"you": p, "self": ref, "vars": {}}))
    if t.get("rush") and from_zone == "graveyard" and d.is_creature():   # アビスラッシュの付随処理
        s.turn_counters[f"rush:{cid}"] = s.turn      # このターン、召喚酔いでもプレイヤーを攻撃できる
        eng._push(eng._child([{"op": "delayed_trigger", "when": {"event": "turn_end"},
                               "effect": [{"op": "move", "select": {"ref": "self_entered"},
                                           "to": "deck", "reason": "put", "position": "bottom"}]}],
                             {"you": p, "self": ref, "vars": {}}))   # ターンの終わりに山札の下へ
    if t.get("sac"):       # ササゲール: 軽減したら破壊する（支払いの一部。実行の解決より先に行う）
        eng._push(eng.ev_task([{"ev": "move", "subject": s.ref(c), "to": "graveyard", "reason": "destroy"}
                               for c in t["sac"]]))
    return None
