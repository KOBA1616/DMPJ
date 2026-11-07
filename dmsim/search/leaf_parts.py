"""探索の葉の評価に足す「部品が揃った度合い」。

ターン内だけの探索では、次のターンのための仕込み（例: 2ターン目に捨てる札でサガを墓地に落とす）に評価がつかない。
そこで葉の評価 evaluate に、ゾーンごとの部品の充足度を足す。勝敗が決まった局面には足さない。
部品表 PartsSpec は手書き（SAGA_SPEC）か、既知コンボ定義 data/known_combos/ から作る（spec_from_combo）。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..engine import Engine
from ..solitaire import Weights, evaluate


@dataclass(frozen=True)
class Part:
    zone: str                 # hand / graveyard / bz / mana ...
    ids: tuple[str, ...]      # このどれかの定義ID（空なら zone 内の「クリーチャー」全般を数える）
    need: int = 1             # この枚数まで加点（それ以上は加点しない）
    weight: float = 1.0       # 1枚あたりの加点


@dataclass(frozen=True)
class PartsSpec:
    parts: tuple[Part, ...]
    coef: float = 1.0         # 全体の倍率


def parts_score(eng: Engine, me: int, spec: PartsSpec) -> float:
    s = eng.s
    total = 0.0
    for p in spec.parts:
        n = 0
        for cid in eng.zlist(p.zone, me):
            d = s.cards[cid].defn
            if (p.ids and d in p.ids) or (not p.ids and "creature" in eng.chars(cid)["types"]):
                n += 1
        total += p.weight * min(n, p.need)
    return spec.coef * total


def make_value_fn(spec: PartsSpec, weights: Weights | None = None):
    """evaluate + 部品スコア。TurnSearch(value_fn=...) に渡す。"""
    w = weights or Weights()

    def value(eng: Engine, me: int) -> float:
        v = evaluate(eng, me, w)
        return v if eng.s.result is not None else v + parts_score(eng, me, spec)
    return value


SAGA = "dm22ex2-021"
# 絶望神サガ: 入口=墓地にサガ + 墓地にクリーチャー2枚（手札から出す経路は別）。手札・場のサガは小さく加点
SAGA_SPEC = PartsSpec((
    Part("graveyard", (SAGA,), 1, 3.0),
    Part("graveyard", (), 2, 1.0),
    Part("hand", (SAGA,), 1, 0.5),
    Part("bz", (SAGA,), 1, 0.5),
))
