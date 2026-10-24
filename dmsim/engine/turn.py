"""ターン構造（500〜512）、カードの実行（601）、マナ支払い（112.2a）。"""
from __future__ import annotations

import itertools

from .registry import task


class TurnMixin:
    def _expire(self, duration: str):
        self.s.continuous = [c for c in self.s.continuous if c["duration"] != duration]

    def _distinct_hand_options(self, p, verb):
        """同じカード名の手札は区別しない（対称な選択肢の正規化）。"""
        seen, out = set(), []
        for cid in self.zlist("hand", p):
            dfn = self.s.cards[cid].defn
            if dfn not in seen:
                seen.add(dfn)
                out.append({"key": f"{verb}:{dfn}", "cid": cid, "name": self.cdef(cid).name})
        return out

    def _mana_choices(self, cid, p) -> list[list[int]]:
        """支払いに使うマナの組（112.2a）。文明は1文明につき別々の1枚で満たし、マナの数値の合計がコストに一致。
        カード名が同じものは区別しない。コスト軽減（112.2b）は未実装。"""
        d = self.cdef(cid)
        if d.cost == 0:
            return [[]]
        untapped = [c for c in self.zlist("mana", p) if not self.s.cards[c].tapped]
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
            if len(out) >= 32:
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


@task("turn")
def h_turn(eng, t):
    s = eng.s
    ph = t["phase"]
    a = s.active
    if ph == "start":                                        # 501
        s.step = "start"
        s.steps_this_turn = 0
        s.turn_counters = {}
        eng._expire(f"until_turn_start:{a}")
        untap = [{"ev": "untap", "subject": s.ref(c)}
                 for c in eng.bz_tops(a) + eng.zlist("mana", a) if s.cards[c].tapped]
        t["phase"] = "draw"
        # ターン起因処理（同時にアンタップ, 702.3a）→「ターンのはじめに」の誘発（501.2）
        eng._push(*([eng.ev_task(untap)] if untap else []), eng.ev_task({"ev": "turn_start", "player": a}))
    elif ph == "draw":                                       # 502
        s.step = "draw"
        t["phase"] = "charge"
        if not (s.turn == 1 and a == s.first_player):       # 500.6
            eng._push(eng.ev_task({"ev": "draw", "player": a}))
    elif ph == "charge":                                     # 503
        s.step = "charge"
        opts = eng._distinct_hand_options(a, "charge") + [{"key": "pass"}]
        ans, d = eng.ask(t, a, "charge", opts)
        if d:
            return d
        t["phase"] = "main"
        o = opts[ans[0]]
        if o["key"] != "pass":
            eng._push(eng.ev_task({"ev": "move", "subject": s.ref(o["cid"]), "to": "mana", "reason": "charge"}))
    elif ph == "main":                                       # 504
        s.step = "main"
        opts = [o for o in eng._distinct_hand_options(a, "play") if eng._mana_choices(o["cid"], a)]
        opts.append({"key": "pass"})
        ans, d = eng.ask(t, a, "main", opts)
        if d:
            return d
        o = opts[ans[0]]
        if o["key"] == "pass":
            t["phase"] = "attack"
        else:
            eng._push({"t": "play", "cid": o["cid"], "player": a, "free": False, "phase": "start"})
    elif ph == "attack":                                     # 505
        s.step = "attack"
        opts = eng._attack_options(a) + [{"key": "pass"}]
        ans, d = eng.ask(t, a, "attack", opts)
        if d:
            return d
        o = opts[ans[0]]
        if o["key"] == "pass":
            t["phase"] = "end"
        else:
            eng._push({"t": "attack", "attacker": s.ref(o["cid"]), "target": o["target"], "phase": 0, "cp": True})
    elif ph == "end":                                        # 511
        s.step = "end"
        t["phase"] = "end2"
        eng._push(eng.ev_task({"ev": "turn_end", "player": a}))
    elif ph == "end2":
        eng._expire("end_of_turn")                          # 511.2
        t["phase"] = "next"
    elif ph == "next":                                       # 512
        for c in list(s.hold):                              # 512.1 保留状態のカードは墓地へ（誘発なし）
            eng._raw_move(c, "graveyard")
        s.active = s.extra_turns.pop(0) if s.extra_turns else 1 - a   # 500.5
        s.turn += 1
        if s.turn > eng.turn_limit:
            s.result = {"winner": None, "reason": "turn_limit", "turn": s.turn}
        t["phase"] = "start"
    return None


@task("play")
def h_play(eng, t):
    """カードの実行（601）。free=True はコストを支払わずに実行（S・トリガー等）。それでも召喚・詠唱したことになる（112.3g）。"""
    s = eng.s
    cid, p = t["cid"], t["player"]
    d = eng.cdef(cid)
    if s.cards[cid].zone != "hand":
        eng._pop(t)
        return None
    if not t["free"]:
        choices = eng._mana_choices(cid, p)
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
    eng._to_hold(cid)
    ref = s.ref(cid)
    if d.is_creature():
        eng._push(eng.ev_task({"ev": "move", "subject": ref, "from": "hand", "to": "bz",
                                 "reason": "summon", "controller": p}))
    else:   # 呪文: 唱えた → 書かれた順に解決 → 最終段階として墓地へ（605.2f）
        env = {"you": p, "eng": ref, "vars": {}}
        eng._push(eng.ev_task({"ev": "cast", "player": p, "subject": ref}),
                   eng._child(d.spell, env),
                   eng.ev_task({"ev": "move", "subject": ref, "from": "hand", "to": "graveyard",
                                 "reason": "resolve"}))
    return None
