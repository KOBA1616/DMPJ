"""公平版ターン探索。真の山札・盾を見ず、決定化した局面で TurnSearch を回して多数決で手を選ぶ。

1手ごとに、観測（見えるカード＋公開イベント）が同じ複数の決定化で TurnSearch を回し、各探索が選んだ
「そのターンの最初の自分の選択」（意味キー）を数えて最多を真の局面に適用する。選んだ後に観測が増える
（めくった等）ので、次の手でまた決定化し直す。真の順序は決定化で捨てるので、結果は観測だけに依存する。"""
from __future__ import annotations

from collections import Counter

from ..engine import Engine
from .turn import TurnSearch, charge_only_policy
from .infoset import determinize
from ..engine.view import active_of, inject_state, state_of


def _own_decision(eng: Engine, me: int, opp_policy):
    """相手の決定を相手役に答えさせて、自分の決定かターン終了まで進める。"""
    while True:
        d = eng.advance()
        if d is None or active_of(eng) != me:
            return None
        if d["player"] == me:
            return d
        eng.answer(opp_policy(eng, d))


class FairTurnSearch:
    def __init__(self, me: int, budget: int = 200, n_det: int = 8, seed: int = 0, weights=None,
                 opp_policy=charge_only_policy, known=(), value_fn=None, lookahead: int = 0):
        self.me, self.budget, self.n_det, self.seed = me, budget, n_det, seed
        self.weights, self.opp_policy, self.known = weights, opp_policy, set(known)
        self.value_fn = value_fn            # 葉の評価の差し替え f(eng, me)。leaf_parts.make_value_fn など
        if lookahead > 0:                   # 複数ターン探索: 葉を次の自分のターンの小探索で評価する（search/multiturn.py）
            from .multiturn import make_lookahead_value_fn
            self.value_fn = make_lookahead_value_fn(value_fn, lookahead, opp_policy, weights)
        self.nodes = 0

    def _vote(self, eng: Engine, d: dict, k: int) -> Counter:
        votes: Counter = Counter()
        base = len(eng.log)
        avail = {o["key"] for o in d["options"]}
        for i in range(self.n_det):
            if i and self._decided(votes, self.n_det - i, avail):
                break                               # 残りの決定化が全部2位に入っても首位は変わらない
            e = eng.clone()
            inject_state(e, determinize(state_of(eng), self.me, self.seed * 1_000_003 + k * 1009 + i, self.known))
            leaf, st = TurnSearch(self.me, self.budget, self.weights, opp_policy=self.opp_policy,
                                value_fn=self.value_fn).run(e)
            self.nodes += st.nodes
            for ent in leaf.log[base:]:
                if ent["p"] == self.me:
                    votes[tuple(ent["keys"])] += 1
                    break
        return votes

    @staticmethod
    def _decided(votes: Counter, remaining: int, avail) -> bool:
        """首位が使える手で、2位との差が残り回数より大きければ、結果（最多の手）は確定している。"""
        mc = votes.most_common(2)
        if not mc or not all(x in avail for x in mc[0][0]):
            return False
        second = mc[1][1] if len(mc) > 1 else 0
        return mc[0][1] - second > remaining

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
