"""診断用: 実際の対局で、中核の札が手札・墓地に来たか、出す手が合法手にあったかを見て、止まった理由を3つに分ける。
tools/route_macro_run.py が DMSIM_WHY=1 のとき使う（既定は使わない。探索・結果は変えず、見るだけ）。

理由（中核の札ごと、最後まで場に出なかった札だけ）:
  a_not_reached: 手札にも墓地にも来なかった（引く量・デッキの問題）
  b_cannot_pay:  手札か墓地に来たが、出す手が合法手に一度も無かった（マナの枚数・文明・進化元の問題）
  c_not_chosen:  出す手が合法手にあったのに選ばなかった（探索の問題。予算切れを含む）
判断ごとの記録はログの各項目に付け、対局の本線のエンジン（assemble.run_one の trace で受け取る）のログだけを読む。
探索の読みは複製した盤面で行われ、そのログは本線に入らないので数えない。
"""
from __future__ import annotations

ZONES = ("hand", "graveyard", "mana", "bz")
_state = {"cards": [], "eng": None}


def install(core_ids):
    from dmsim.engine import core
    from dmsim.eval import assemble
    _state["cards"] = list(core_ids)
    if getattr(core.Engine, "_why_orig", None) is None:
        core.Engine._why_orig = core.Engine.answer
        orig = core.Engine._why_orig

        def answer(self, choice):
            s = self.s
            w = s.waiting
            info = None
            if w and _state["cards"]:
                keys = [o["key"] for o in w.get("options", [])]
                mana = s.zones["mana"][0]
                dark = sum(1 for c in mana if "darkness" in self.rules.cards[s.cards[c].defn].civs)
                loc = {cid: [sum(1 for c in s.zones[z][0] if s.cards[c].defn == cid) for z in ZONES] for cid in _state["cards"]}
                opt = [cid for cid in _state["cards"] if any(k.startswith("play:" + cid) for k in keys)]
                gc = sum(1 for c in s.zones["graveyard"][0] if self.rules.cards[s.cards[c].defn].is_creature)
                info = (s.turn, loc, opt, len(mana), dark, gc)
            rv = orig(self, choice)
            if info and self.log:
                self.log[-1]["_why"] = info
            return rv
        core.Engine.answer = answer
        orun = assemble.run_one

        def run_one(*a, trace=None, **k):
            def tr(e, t):
                _state["eng"] = e
                if trace:
                    trace(e, t)
            return orun(*a, trace=tr, **k)
        assemble.run_one = run_one


def reset():
    _state["eng"] = None


def result():
    e = _state["eng"]
    if e is None:
        return {}
    rec = {}
    for x in e.log:
        info = x.get("_why")
        if not info or x.get("p") != 0:
            continue
        turn, loc, opt, nm, dk, gc = info
        for cid, (h, g, m, bz) in loc.items():
            r = rec.setdefault(cid, {"reach": None, "opt": 0, "bz": False})
            r["bz"] |= bool(bz)
            if r["reach"] is None and (h or g):
                r["reach"], r["mana_at_reach"] = turn, [nm, dk]
            r["opt"] += cid in opt
            r["last_mana"] = [nm, dk]
            if h:
                r["hand_turns"] = r.get("hand_turns", 0) + 1
                r["in_hand_last"] = [turn, nm, dk, gc]
    out = {}
    for cid, r in rec.items():
        if r["bz"]:
            continue
        why = "a_not_reached" if r["reach"] is None else ("c_not_chosen" if r["opt"] else "b_cannot_pay")
        out[cid] = {"why": why, "reach_turn": r["reach"], "mana_at_reach": r.get("mana_at_reach"), "last_mana": r.get("last_mana"),
                   "in_hand_last": r.get("in_hand_last"), "where": "hand" if r.get("hand_turns") else "graveyard"}
    return out
