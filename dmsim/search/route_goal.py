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
        cids = s.zones[z][owner]
        if p.get("top") and z == "bz":       # 場の一番上の札だけ（進化元として下にある札を除く）
            below = {u for c in cids for u in s.cards[c].under}
            cids = [c for c in cids if c not in below]
        for c in cids:
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


def route_score(eng, stages, me: int = 0, floor: int = 0) -> float:
    """floor: その対局で既に達成した段（ラチェット）。局面が前の段の状態を消しても、達成済みの段の点は下げない。"""
    k = max(reached(eng, stages, me), floor)
    return sum(st.weight for st in stages[:k])


LIVE_ZONES = ("hand", "graveyard", "bz")   # 名前の札が「まだ経路で使える」とみなす公開・手元のゾーン（部分点用）
AWAY_ZONES = ("mana",)                     # 経路の段がそのゾーンを指していなければ「使えない場所」とみなす（減点用）


def _frac(eng, p: dict, me: int, elsewhere: float) -> float:
    """述語 p の進み具合 0..1。>= の枚数条件は count/n。名前の札が指すゾーンに無くても使える場所にあれば elsewhere。"""
    if p.get("op", ">=") != ">=":
        return 1.0 if holds(eng, p, me) else 0.0
    n = max(1, p.get("n", 1))
    f = min(count(eng, p, me) / n, 1.0)
    if f < 1.0 and "name" in p.get("match", {}) and elsewhere > 0:
        zones = set((p["zone"],) if p.get("zone") else tuple(p.get("zones") or ()))
        other = {**p, "zone": None, "zones": [z for z in LIVE_ZONES if z not in zones]}
        if other["zones"] and count(eng, other, me) > 0:
            f = max(f, elsewhere)
    return f


def partial_score(eng, stages, me: int = 0, elsewhere: float = 0.25, floor: int = 0) -> float:
    """次の未達成の段（満たした最も後ろの段か floor の次）の進み具合 × その段の weight。"""
    k = max(reached(eng, stages, me), floor)
    if k >= len(stages):
        return 0.0
    preds = stages[k].preds
    return stages[k].weight * sum(_frac(eng, p, me, elsewhere) for p in preds) / len(preds)


def needed_cards(stages) -> dict[str, tuple[int, set]]:
    """経路の段から導く {札の名前: (必要枚数の最大, その札を指すゾーンの集合)}。"""
    out: dict[str, tuple[int, set]] = {}
    for st in stages:
        for p in st.preds:
            nm = p.get("match", {}).get("name")
            if nm is None or p.get("owner", 0) != 0:
                continue
            zones = set((p["zone"],) if p.get("zone") else tuple(p.get("zones") or ()))
            n0, z0 = out.get(nm, (0, set()))
            out[nm] = (max(n0, p.get("n", 1)), z0 | zones)
    return out


def away_penalty(eng, need: dict, me: int = 0) -> float:
    """経路に要る札が、経路の段が指さないゾーン（マナ）に置かれた枚数（必要枚数まで）。"""
    tot = 0
    for nm, (n, zones) in need.items():
        for z in AWAY_ZONES:
            if z not in zones:
                tot += min(count(eng, {"zone": z, "match": {"name": nm}}, me), n)
    return float(tot)


def make_value_fn(stages, weights: Weights | None = None, *, mult: float = 1.0, partial: bool = False,
                  elsewhere: float = 0.25, away: float = 0.0, ratchet: list | None = None,
                  lookahead_last: int = 0, opp_policy=None):
    """evaluate + mult × (経路の点 [+ 次の段の部分点] − away × 使えないゾーンへ送った経路の札の枚数)。
    既定（partial=False, away=0, mult=1）は段を満たした分だけ（PR #423 と同じ）。勝敗が決まった局面には足さない。
    lookahead_last: >0 なら、入口の直前の段まで達成した葉に限り、次の自分のターンを予算 lookahead_last で探索して良い方を採る
      （search.multiturn.make_lookahead_value_fn と同じ。全部の葉にかけないので計算量の増加が小さい）。
    ratchet: [k] を渡すと、その対局で達成済みの段 k を下限にする（呼び出し側が各ターンの後に k を更新する。note_reached）。"""
    w = weights or Weights()
    need = needed_cards(stages) if away else {}

    def value(eng, me: int) -> float:
        v = evaluate(eng, me, w)
        if result_of(eng) is not None:
            return v
        fl = ratchet[0] if ratchet else 0
        r = route_score(eng, stages, me, fl)
        if partial:
            r += partial_score(eng, stages, me, elsewhere, fl)
        if away:
            r -= away * away_penalty(eng, need, me)
        return v + mult * r
    if not lookahead_last:
        return value
    from .multiturn import make_lookahead_value_fn
    from .turn import charge_only_policy
    deep = make_lookahead_value_fn(value, lookahead_last, opp_policy or charge_only_policy, w)
    last = len(stages) - 1

    def gated(eng, me: int) -> float:
        if result_of(eng) is None and max(reached(eng, stages, me), ratchet[0] if ratchet else 0) >= last:
            return deep(eng, me)
        return value(eng, me)
    return gated


def note_reached(eng, stages, ratchet: list, me: int = 0) -> None:
    """ラチェットの更新: 真の局面で満たした段が今の下限より後ろなら上げる（下げない）。"""
    ratchet[0] = max(ratchet[0], reached(eng, stages, me))
