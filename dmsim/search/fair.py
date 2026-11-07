"""公平版ターン探索。真の山札・盾を見ず、決定化した局面で TurnSearch を回して多数決で手を選ぶ。

1手ごとに、観測（見えるカード＋公開イベント）が同じ複数の決定化で TurnSearch を回し、各探索が選んだ
「そのターンの最初の自分の選択」（意味キー）を数えて最多を真の局面に適用する。選んだ後に観測が増える
（めくった等）ので、次の手でまた決定化し直す。真の順序は決定化で捨てるので、結果は観測だけに依存する。"""
from __future__ import annotations

from collections import Counter

from ..engine import Engine
from ..solitaire import TurnSearch, charge_only_policy
from .infoset import determinize


def _own_decision(eng: Engine, me: int, opp_policy):
    """相手の決定を相手役に答えさせて、自分の決定かターン終了まで進める。"""
    while True:
        d = eng.advance()
        if d is None or eng.s.active != me:
            return None
        if d["player"] == me:
            return d
        eng.answer(opp_policy(eng, d))


class FairTurnSearch:
    def __init__(self, me: int, budget: int = 200, n_det: int = 8, seed: int = 0, weights=None,
                 opp_policy=charge_only_policy, known=()):
        self.me, self.budget, self.n_det, self.seed = me, budget, n_det, seed
        self.weights, self.opp_policy, self.known = weights, opp_policy, set(known)
        self.nodes = 0

    def _vote(self, eng: Engine, d: dict, k: int) -> Counter:
        votes: Counter = Counter()
        base = len(eng.log)
        for i in range(self.n_det):
            e = eng.clone()
            e.s = determinize(eng.s, self.me, self.seed * 1_000_003 + k * 1009 + i, self.known)
            leaf, st = TurnSearch(self.me, self.budget, self.weights, opp_policy=self.opp_policy).run(e)
            self.nodes += st.nodes
            for ent in leaf.log[base:]:
                if ent["p"] == self.me:
                    votes[tuple(ent["keys"])] += 1
                    break
        return votes

    def run(self, eng: Engine) -> Engine:
        """eng（自分の決定待ち）から自分のターンを最後まで進めた Engine を返す。eng は変更しない。"""
        eng = eng.clone()
        k = 0
        while (d := _own_decision(eng, self.me, self.opp_policy)) is not None:
            votes = self._vote(eng, d, k)
            k += 1
            avail = [o["key"] for o in d["options"]]
            for keys, _ in votes.most_common():
                if all(x in avail for x in keys):
                    eng.answer_by_keys(list(keys))
                    break
            else:                                   # 投票が使えない時は先頭の選択肢（最小数）
                eng.answer(list(range(d["min"])) if d["min"] else [0])
        return eng
