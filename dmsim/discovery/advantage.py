"""局面評価 V（勝敗を使わない）と、カードの組の相乗効果 S の測定。

V = 自分の資源の換算値 − 相手の資源の換算値。換算規則は data/discovery/advantage_weights.yaml（資源1単位の価値）。
相乗効果 S(A,B) = V(A,B) − V(A) − V(B) + V(なし)。1ターン分の局面から測る（play_game で自分の1ターンを回す）。
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..defs import DATA
from ..engine.core import Engine

RES = ("hand", "shield", "mana", "board", "board_power", "graveyard", "deck")


def load_weights(path: Path | None = None) -> dict:
    return yaml.safe_load((path or DATA / "discovery" / "advantage_weights.yaml").read_text(encoding="utf-8"))


def resource_vector(eng: Engine, p: int) -> dict:
    """プレイヤー p の資源量（事実の記録）。"""
    mine = eng.bz_tops(p)
    power = sum(eng.chars(c).get("power") or 0 for c in mine if "creature" in eng.chars(c)["types"])
    return {"hand": len(eng.zlist("hand", p)), "shield": len(eng.zlist("shield", p)), "mana": len(eng.zlist("mana", p)),
            "board": len(mine), "board_power": power, "graveyard": len(eng.zlist("graveyard", p)), "deck": len(eng.zlist("deck", p))}


def value(vec_me: dict, vec_opp: dict, w: dict) -> float:
    """V = 自分の換算値 − 相手の換算値。"""
    return sum(w["self"].get(k, 0.0) * v for k, v in vec_me.items()) - sum(w["opp"].get(k, 0.0) * v for k, v in vec_opp.items())


def board_value(eng: Engine, me: int, w: dict | None = None) -> float:
    w = w or load_weights()
    return value(resource_vector(eng, me), resource_vector(eng, 1 - me), w)


def turn_value(rules, spec: dict, w: dict | None = None, turns: int = 1, budget: int = 200) -> tuple[float, dict]:
    """spec（scenario.build 形式）の局面から自分の turns ターンを AI に回させ、終了時の V と自分の資源ベクトルを返す。"""
    from .. import scenario
    w = w or load_weights()
    from ..solitaire import play_game
    start = scenario.build(rules, spec)
    _, eng = play_game(rules, [], [], 1, max_turn=turns, budget=budget, start=start, lock_rounds=0,
                       value_fn=lambda e, me: board_value(e, me, w))
    return board_value(eng, 0, w), resource_vector(eng, 0)


def synergy(rules, a: dict, b: dict, base: dict, opp: dict | None = None, w: dict | None = None, turns: int = 1,
            seeds=(1, 2, 3)) -> dict:
    """a, b: 自分側の配置（{ゾーン: [カード...]}）の追加分。base: 共通の配置。S = V(A,B) − V(A) − V(B) + V(なし)。"""
    def merge(*parts):
        out = {}
        for part in parts:
            for z, cards in (part or {}).items():
                out[z] = out.get(z, []) + list(cards)
        return out
    cases = {"none": merge(base), "a": merge(base, a), "b": merge(base, b), "ab": merge(base, a, b)}
    vals = {k: [] for k in cases}
    for sd in seeds:
        for k, p0 in cases.items():
            vals[k].append(turn_value(rules, {"p0": p0, "p1": opp or {}, "seed": sd}, w, turns)[0])
    mean = {k: sum(v) / len(v) for k, v in vals.items()}
    return {"S": mean["ab"] - mean["a"] - mean["b"] + mean["none"], "mean": mean, "seeds": list(seeds)}


PLACES = ("hand", "graveyard", "mana", "bz")


def scan_pair(rules, a: str, b: str, base: dict | None = None, opp: dict | None = None, places=PLACES,
              w: dict | None = None, turns: int = 1, seeds=(1, 2, 3)) -> list[dict]:
    """カード a, b を置き場所の全組み合わせに置いたときの相乗効果 S を測り、S の大きい順に返す。
    「どこにいれば組が成立するか」の記録になる（例: 騎士は手札、DMC は墓地でも手札でもよい）。"""
    out = []
    for pa in places:
        for pb in places:
            r = synergy(rules, {pa: [a]}, {pb: [b]}, base or {}, opp=opp, w=w, turns=turns, seeds=seeds)
            out.append({"a": a, "b": b, "place_a": pa, "place_b": pb, "S": r["S"], "mean": r["mean"]})
    return sorted(out, key=lambda x: -x["S"])
