"""攻撃ステップ（505〜510）、バトル（701.13）、ブレイクとS・トリガー（509.5, 113.6）。"""
from __future__ import annotations

from .registry import task


class CombatMixin:
    def _can_attack(self, cid) -> bool:
        c = self.s.cards[cid]
        ch = self.chars(cid)
        if c.tapped or "creature" not in ch["types"]:
            return False
        return c.entered_turn != self.s.turn or "speed_attacker" in ch["keywords"]   # 506.1a

    def _attack_options(self, a):
        out = []
        for cid in self.bz_tops(a):
            if not self._can_attack(cid):
                continue
            dfn = self.s.cards[cid].defn
            if "cannot_attack_player" not in self.chars(cid)["keywords"]:
                out.append({"key": f"attack:{dfn}:player", "cid": cid, "target": "player"})
            for tc in self.bz_tops(1 - a):
                if self.s.cards[tc].tapped:                      # 505.2
                    out.append({"key": f"attack:{dfn}:{self.s.cards[tc].defn}", "cid": cid,
                                "target": self.s.ref(tc)})
        return out

    def _battle(self, x, y):
        """バトル（701.13）。結果で誘発した効果はその場で解決してからバトルを終える。"""
        px, py = self.chars(x[0])["power"], self.chars(y[0])["power"]
        losers = ([x] if px <= py else []) + ([y] if py <= px else [])
        evs = [{"ev": "move", "subject": r, "to": "graveyard", "reason": "destroy"} for r in losers]
        return self._window(self.ev_task(evs)) if evs else []


@task("attack")
def h_attack(eng, t):
    """攻撃ステップのサブステップ（506〜510）。cp=True なので各段階の間に待機効果を解決する。"""
    s = eng.s
    att = t["attacker"]
    a = s.active
    ph = t["phase"]
    if ph == 0:                                               # 506 攻撃クリーチャー指定
        t["phase"] = 1
        s.cards[att[0]].tapped = True
        eng._push(eng.ev_task({"ev": "attack", "subject": att, "target": t["target"], "controller": a}))
        return None
    if ph < 4 and (not s.alive(att) or (t["target"] != "player" and not s.alive(t["target"]))):
        t["phase"] = 4                                        # 505.6a 攻撃から取り除かれたら攻撃終了へ
        return None
    if ph == 1:                                               # 507 ブロッククリーチャー指定
        blockers = [c for c in eng.bz_tops(1 - a)
                    if not s.cards[c].tapped and "blocker" in eng.chars(c)["keywords"]
                    and [c, s.cards[c].gen] != t["target"]]
        opts = [eng._card_option(c) for c in blockers] + [{"key": "no_block"}]
        ans, d = eng.ask(t, 1 - a, "block", opts)
        if d:
            return d
        t["phase"] = 2
        o = opts[ans[0]]
        if o["key"] != "no_block":
            s.cards[o["cid"]].tapped = True
            t["target"] = s.ref(o["cid"])
            t["blocked"] = True
            eng._push(eng.ev_task({"ev": "block", "subject": t["target"], "attacker": att,
                                     "controller": 1 - a}))
        return None
    if ph == 2:                                               # 508 バトル
        t["phase"] = 3
        if t["target"] != "player":
            eng._push(*eng._battle(att, t["target"]))
        return None
    if ph == 3:                                               # 509 ダイレクトアタック
        t["phase"] = 4
        if t["target"] == "player":
            shields = eng.zlist("shield", 1 - a)
            if shields:
                kw = eng.chars(att[0])["keywords"]
                n = 3 if "triple_breaker" in kw else 2 if "double_breaker" in kw else 1
                eng._push({"t": "break", "victim": 1 - a, "by": a, "count": n, "phase": 0, "in_effect": False})
            else:
                s.result = {"winner": a, "reason": "direct_attack", "turn": s.turn}   # 509.1 / 703.4a
        return None
    eng._expire("during_attack")                             # 510.2
    eng._pop(t)
    return None


@task("break")
def h_break(eng, t):
    """ブレイク: 選ぶ → S・トリガー宣言 → 同時に手札へ → S・トリガーを解決（509.3〜509.5, 113.6）。"""
    s = eng.s
    victim = t["victim"]
    shields = eng.zlist("shield", victim)
    if t["phase"] == 0:
        n = min(t["count"], len(shields))
        opts = [eng._card_option(c) for c in shields]
        ans, d = eng.ask(t, t["by"], "choose_shields", opts, n, n)
        if d:
            return d
        t["chosen"] = [shields[i] for i in ans]
        t["phase"] = 1
        return None
    trig = [c for c in t["chosen"] if "s_trigger" in eng.cdef(c).keywords]
    opts = [{"key": f"strigger:{s.cards[c].defn}", "cid": c} for c in trig]
    declared = []
    if opts:
        ans, d = eng.ask(t, victim, "declare_strigger", opts, 0, len(opts))
        if d:
            return d
        declared = [opts[i]["cid"] for i in ans]
    eng._pop(t)
    seq = [eng.ev_task([{"ev": "move", "subject": s.ref(c), "to": "hand", "reason": "break"}
                         for c in t["chosen"]]),
           {"t": "enqueue_st", "cids": declared, "player": victim},
           eng.ev_task({"ev": "break", "player": victim, "count": len(t["chosen"])})]
    if t["in_effect"]:   # 効果の解決中のブレイクは、S・トリガーをその場で解決する（101.4g）
        seq = eng._window(*seq, only_st=True)
    eng._push(*seq)
    return None


@task("enqueue_st")
def h_enqueue_st(eng, t):
    s = eng.s
    eng._pop(t)
    win = s.windows[-1] if s.windows else 0
    for c in t["cids"]:
        if s.cards[c].zone == "hand":
            s.seq += 1
            s.pending.append({"pid": s.seq, "kind": "strigger", "win": win, "controller": t["player"],
                              "src": s.ref(c), "defn": s.cards[c].defn, "ab": -1, "env": {}})
    return None
