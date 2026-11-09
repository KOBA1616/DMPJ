"""準備札（タイフーン等、手札を整えて墓地へ落とす札）を撃つことへの加点。

評価が部品の揃いしか見ないと、揃う前の準備札（引いて捨てる呪文）を撃つ価値が評価に出ず、AIが撃たない。
葉の評価に「準備札が墓地に行った枚数」の加点を足す（足切りには使わない）。自動修正の Knobs.prep_bonus で重みを振る。
"""
from __future__ import annotations

from ..engine import Engine
from ..eval.stage import count_matching
from ..engine_view import result_of


def prep_used(eng: Engine, me: int, ids) -> int:
    """準備札が墓地に行った枚数（撃った・捨てた）。"""
    return count_matching(eng, me, "graveyard", tuple(ids)) if ids else 0


def with_prep_bonus(inner, ids, bonus: float, cap: int = 2):
    """inner(eng, me) に bonus × min(cap, 墓地の準備札) を足す。勝敗が決まった局面には足さない。"""
    ids = tuple(ids)

    def value(eng: Engine, me: int) -> float:
        v = inner(eng, me)
        return v if result_of(eng) is not None else v + bonus * min(cap, prep_used(eng, me, ids))
    return value
