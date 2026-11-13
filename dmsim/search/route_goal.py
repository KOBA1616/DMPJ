"""コンボの経路を「段の列」として葉の評価に足す（ロードマップ P3 の先行実験。既定では使わない）。

経路データ data/loops/route/<名前>.yaml: stages = [{name, weight, all: [述語...]} | {name, weight, entry: <入口名>}]。
述語は入口 data/loops/entry/ の minimal と同じ形（zone|zones, match{name|types|civs|races}, n, op, owner=0）。
局面の点は「満たしている段のうち最も後ろの段」までの weight の合計。後の段が前の段の状態を消してもよい。
探索の手順（TurnSearch の候補・払い方）には触れず、葉の評価 value_fn だけを差し替える。カード名はデータ側にだけ書く。
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import yaml

from ..base.store import REPO
from ..engine.view import result_of
from .leaf_eval import Weights, evaluate

ROUTE_DIR = REPO / "data" / "loops" / "route"
ENTRY_DIR = REPO / "data" / "loops" / "entry"
OPS = {">=": lambda k, n: k >= n, "<=": lambda k, n: k <= n, "==": lambda k, n: k == n}


@dataclass(frozen=True)
class Stage:
    name: str
    weight: float
    preds: tuple[dict, ...]


def _entry_preds(name: str) -> tuple[dict, ...]:
    d = json.loads((ENTRY_DIR / f"{name}.json").read_text(encoding="utf-8"))
    return tuple(d["minimal"])


def load(name: str) -> tuple[Stage, ...]:
    y = yaml.safe_load((ROUTE_DIR / f"{name}.yaml").read_text(encoding="utf-8"))
    out = []
    for s in y["stages"]:
        preds = _entry_preds(s["entry"]) if "entry" in s else tuple(s["all"])
        out.append(Stage(s["name"], float(s["weight"]), preds))
    return tuple(out)


def count(eng, p: dict, me: int = 0) -> int:
    """owner は 0=自分（me）, 1=相手。"""
    s, rules = eng.s, eng.rules
    owner = me if p.get("owner", 0) == 0 else 1 - me
    zones = (p["zone"],) if p.get("zone") else tuple(p.get("zones") or ())
    m = p.get("match", {})
    n = 0
    for z in zones:
        for c in s.zones[z][owner]:
            defn = s.cards[c].defn
            d = rules.cards[defn]
            if "name" in m and m["name"] not in (defn, d.id):
                continue
            if "types" in m and not set(m["types"]) & set(d.types):
                continue
            if "civs" in m and not set(m["civs"]) & set(d.civs):
                continue
            if "races" in m and not set(m["races"]) & set(d.races):
                continue
            n += 1
    return n


def holds(eng, p: dict, me: int = 0) -> bool:
    return OPS[p.get("op", ">=")](count(eng, p, me), p.get("n", 1))


def reached(eng, stages, me: int = 0) -> int:
    """満たしている段のうち最も後ろの段の番号（1始まり）。どれも満たさなければ 0。"""
    k = 0
    for i, st in enumerate(stages, 1):
        if all(holds(eng, p, me) for p in st.preds):
            k = i
    return k


def route_score(eng, stages, me: int = 0) -> float:
    k = reached(eng, stages, me)
    return sum(st.weight for st in stages[:k])


def make_value_fn(stages, weights: Weights | None = None):
    """evaluate + 経路の点。FairTurnSearch / TurnSearch の value_fn に渡す。勝敗が決まった局面には足さない。"""
    w = weights or Weights()

    def value(eng, me: int) -> float:
        v = evaluate(eng, me, w)
        return v if result_of(eng) is not None else v + route_score(eng, stages, me)
    return value
