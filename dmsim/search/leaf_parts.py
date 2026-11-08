"""探索の葉の評価に足す「部品が揃った度合い」。

ターン内だけの探索では、次のターンのための仕込み（例: 2ターン目に捨てる札でサガを墓地に落とす）に評価がつかない。
そこで葉の評価 evaluate に、ゾーンごとの部品の充足度を足す。勝敗が決まった局面には足さない。
部品表 PartsSpec は手書き（SAGA_SPEC）か、既知コンボ定義 data/known_combos/ から作る（spec_from_combo）。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from ..engine import Engine
from ..eval.stage import count_matching
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
    total = 0.0
    for p in spec.parts:
        total += p.weight * min(count_matching(eng, me, p.zone, p.ids), p.need)
    return spec.coef * total


def make_value_fn(spec: PartsSpec, weights: Weights | None = None):
    """evaluate + 部品スコア。TurnSearch(value_fn=...) に渡す。"""
    w = weights or Weights()

    def value(eng: Engine, me: int) -> float:
        v = evaluate(eng, me, w)
        return v if eng.s.result is not None else v + parts_score(eng, me, spec)
    return value


# 絶望神サガ: キル手前(T3開始)の最小局面は、墓地にサガ+シャコガイル+クリーチャー1体、手札にサガ+ドラゲリオン、
# 水・闇のマナ3（data/eval/saga_near_kill を縮めて確認: シャコガイルが墓地に無い/ドラゲリオンかサガが手札に無いと起動しない）。
# coef=10: evaluate の打点項（場のクリーチャー1体で+40）に勝てる大きさが必要。1〜5 では saga_entry の T2 墓地サガ率が 4/40 のまま、10 で 12/40
KNOWN_COMBOS = Path(__file__).resolve().parents[2] / "data" / "known_combos" / "combos.yaml"
# 既定の導出: core 部品（id あり）を手札・場に置くほど加点、墓地は少なめ、マナは0（チャージで潰さないよう手札優先）
DEFAULT_ZONE_WEIGHTS = (("hand", 1.0), ("bz", 1.0), ("graveyard", 0.5))


def spec_from_combo(combo: dict, coef: float = 10.0) -> PartsSpec:
    """known_combos の1件から部品表を作る。combo に leaf_parts（手書きの [{zone, ids, need, weight}]）があればそれを使い、
    なければ core 部品（id あり）ごとに DEFAULT_ZONE_WEIGHTS で作る。同じ id の部品は1つにまとめる（枚数は need に足す）。"""
    if combo.get("leaf_parts"):
        return PartsSpec(tuple(Part(p["zone"], tuple(p.get("ids", ())), p.get("need", 1), p.get("weight", 1.0))
                               for p in combo["leaf_parts"]), coef=combo.get("leaf_coef", coef))
    ids = list(dict.fromkeys(p["id"] for p in combo["parts"] if p.get("role") == "core" and p.get("id")))
    return PartsSpec(tuple(Part(z, (i,), 1, w) for i in ids for z, w in DEFAULT_ZONE_WEIGHTS), coef=coef)


def load_specs(path: Path = KNOWN_COMBOS, split: str | None = None) -> dict[str, PartsSpec]:
    """既知コンボの id → 部品表。split（tuning / holdout）で絞れる。検証専用(holdout)は調整に使わないこと。"""
    combos = yaml.safe_load(Path(path).read_text(encoding="utf-8"))["combos"]
    return {c["id"]: spec_from_combo(c) for c in combos if split in (None, c.get("split"))}


SAGA = "dm22ex2-021"
DRAGELION, SHAKOGAIRU, ET = "dm22ex1-007", "dmrp03-s03", "dm26ex2-071"
# 絶望神サガ: 手書きの値は data/known_combos/combos.yaml の saga.leaf_parts にある。
# キル手前(T3開始)の最小局面は、墓地にサガ+シャコガイル+クリーチャー1体、手札にサガ+ドラゲリオン、水・闇のマナ3
# （data/eval/saga_near_kill を縮めて確認）。coef=10 は evaluate の打点項（場のクリーチャー1体で+40）に勝てる大きさ。
SAGA_SPEC = load_specs()["saga"]
