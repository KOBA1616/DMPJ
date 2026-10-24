"""ターン構造（500〜512）、カードの実行（601）、マナ支払い（112.2a）。

ターンはステップの列（data/rules/turn.yaml）で、各ステップの処理は @step で登録する。
ターンが始まる時に state.step_mods（効果による「飛ばす」「もう一度行う」）を反映した列を作る。
"""
from __future__ import annotations

import itertools

from ..types import PlayTask, TurnTask
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
        return out

    def _can_play_face(self, cid, p, face) -> bool:
        f = self.cdef(cid).face(face)
        action = "summon" if f.is_creature() else "cast"
        if not self.permits(cid, action):
            return False
        if "evolution" in f.types and not self._evo_sources(cid, p, face):
            return False
        return bool(self._mana_choices(cid, p, face, limit=1))

    def _evo_sources(self, cid, p, face=None) -> list[int]:
        """適正な進化元（801.1a）。自分のバトルゾーンのクリーチャーで evolve_from を満たすもの。"""
        f = self.cdef(cid).face(face)
        return [c for c in self.bz_tops(p)
                if "creature" in self.chars(c)["types"] and self.filter_match(c, f.evolve_from or {})]

    def _mana_choices(self, cid, p, face=None, limit: int = 32) -> list[list[int]]:
        """支払いに使うマナの組（112.2a）。文明は1文明につき別々の1枚で満たし、マナの数値の合計がコストに一致。
        カード名が同じものは区別しない。コスト軽減（112.2b）は未実装。"""
        d = self.cdef(cid).face(face)
        if d.cost == 0:
            return [[]]
        untapped = [c for c in self.zlist("mana", p) if not self.s.cards[c].tapped]
        if len(untapped) < len(d.civs) or sum(self.cdef(c).mana for c in untapped) < d.cost:
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
                if total == d.cost and civ_ok(cnt):
                    out.append([c for n, k in zip(names, cnt) for c in groups[n][:k]])
                return
            cap = len(groups[names[i]])
            for k in range(min(cap, (d.cost - total) // mana[i] if mana[i] else len(need) - zeros), -1, -1):
                dfs(i + 1, cnt + [k], total + k * mana[i], zeros + (0 if mana[i] else k))

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
    opts = eng._play_options(a) + [{"key": "pass"}]
    ans, d = eng.ask(t, a, "main", opts)
    if d:
        return d
    o = opts[ans[0]]
    if o["key"] == "pass":
        eng._step_done(t)
    else:
        eng._push(eng.play_task(o["cid"], a, False, o.get("face")))


@step("attack")
def st_attack(eng, t):                                  # 505
    s = eng.s
    a = s.active
    opts = eng._attack_options(a) + [{"key": "pass"}]
    ans, d = eng.ask(t, a, "attack", opts)
    if d:
        return d
    o = opts[ans[0]]
    if o["key"] == "pass":
        eng._step_done(t)
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
    action = "summon" if d.is_creature() else "cast"
    if not eng.permits(cid, action):
        eng._pop(t)
        return None
    if "evolution" in d.types and "evo" not in t:
        srcs = eng._evo_sources(cid, p, face)
        if not srcs:
            eng._pop(t)
            return None
        opts = [eng._card_option(c) for c in srcs]
        ans, dd = eng.ask(t, p, "choose_evo_source", opts)
        if dd:
            return dd
        t["evo"] = s.ref(srcs[ans[0]])
    if not t["free"]:
        choices = eng._mana_choices(cid, p, face)
        if not choices:
            eng._pop(t)
            return None
        opts = [{"key": "mana:" + ",".join(sorted(s.cards[c].defn for c in ch)), "cids": ch} for ch in choices]
        ans, dd = eng.ask(t, p, "pay_mana", opts)
        if dd:
            return dd
        for c in opts[ans[0]]["cids"]:
            s.cards[c].tapped = True
    eng._pop(t)
    from_zone = s.cards[cid].zone
    eng._to_hold(cid)
    if face is not None:
        s.cards[cid].face = face
    ref = s.ref(cid)
    if d.is_creature():
        ev = {"ev": "move", "subject": ref, "from": from_zone, "to": "bz", "reason": "summon", "controller": p}
        if t.get("evo"):
            ev["stack_on"] = t["evo"]
        eng._push(eng.ev_task(ev))
    else:   # 呪文: 唱えた → 書かれた順に解決 → 最終段階として墓地へ（605.2f）
        env = {"you": p, "self": ref, "vars": {}}
        if t.get("st"):
            env["in_st"] = True
        eng._push(eng.ev_task({"ev": "cast", "player": p, "subject": ref}),
                   eng._child(d.spell, env),
                   eng.ev_task({"ev": "move", "subject": ref, "from": from_zone, "to": d.resolve_to,
                                 "reason": "resolve"}),
                   *([eng._child(d.after_resolve, env)] if d.after_resolve else []))
    return None
