"""複数ターン探索（仕込みターン→起動ターン）。

ターン内探索 TurnSearch の葉（自分のターン終了局面）の評価に「次の自分のターンを小さく探索した結果」を使う。
葉から相手のターンを相手役で進め、次の自分のターンを少ない予算で探索し、その葉の評価と手前の評価の大きいほうを返す。
こうすると「今のターンでは何も起きないが、次のターンに勝ちへつながる仕込み」（墓地へのサガ落とし等）が価値を持つ。
FairTurnSearch の決定化した局面の上で動くので、山札の真の順序は見ない（決定化ごとの次のドローが入るだけ）。
評価値は足切りに使わず、手の順位づけだけに使う。エンジンは編集しない。
"""
from __future__ import annotations

from ..engine import Engine
from .leaf_eval import Weights, evaluate
from .turn import TurnSearch, charge_only_policy
from ..engine_view import active_of, result_of


def advance_to_own_turn(eng: Engine, me: int, opp_policy, limit: int = 400) -> bool:
    """相手のターンを相手役で進め、自分の次の決定まで進める。進められたら True（ゲーム終了・打ち切りは False）。"""
    for _ in range(limit):
        d = eng.advance()
        if d is None:
            return False
        if d["player"] == me and active_of(eng) == me:
            return True
        eng.answer(opp_policy(eng, d))
    return False


def make_lookahead_value_fn(inner=None, budget: int = 20, opp_policy=charge_only_policy,
                            weights: Weights | None = None, burn_stock: bool = False):
    """葉の評価 f(eng, me) を、次の自分のターンの探索結果で底上げした関数にする。

    inner: 基になる評価（None なら evaluate）。次ターンの探索の葉にも同じ inner を使う。"""
    w = weights or Weights()
    base_fn = inner or (lambda e, m: evaluate(e, m, w))

    def value(eng: Engine, me: int) -> float:
        base = base_fn(eng, me)
        if result_of(eng) is not None or active_of(eng) == me:
            return base                              # 勝敗が決まった／自分のターンの途中（葉でない）
        e = eng.clone()
        if not advance_to_own_turn(e, me, opp_policy) or result_of(e) is not None:
            return base if result_of(e) is None else max(base, base_fn(e, me))
        ts = TurnSearch(me, budget, w, opp_policy=opp_policy, value_fn=base_fn)
        ts.burn_stock = burn_stock
        leaf, _ = ts.run(e)
        return max(base, base_fn(leaf, me))
    return value
