"""局面評価 V（勝敗を使わない）と、カードの組の相乗効果 S の測定。

V = 自分の資源の換算値 − 相手の資源の換算値。換算規則は data/discovery/advantage_weights.yaml（資源1単位の価値）。
相乗効果 S(A,B) = V(A,B) − V(A) − V(B) + V(なし)。1ターン分の局面から測る（play_game で自分の1ターンを回す）。
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..cards.defs import DATA
from ..engine.core import Engine
from dmsim.engine.view import trace_of, trace_on

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
    from dmsim.engine import scenario
    w = w or load_weights()
    from ..search.game import play_game
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
    per_seed = [vals["ab"][i] - vals["a"][i] - vals["b"][i] + vals["none"][i] for i in range(len(seeds))]
    return {"S": mean["ab"] - mean["a"] - mean["b"] + mean["none"], "mean": mean, "seeds": list(seeds), "per_seed": per_seed}


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


def combo_report(rules, a: dict, b: dict, base: dict, opp: dict | None = None, w: dict | None = None, turns: int = 1,
                 seeds=(1, 2, 3)) -> dict:
    """コンボの定義（手順あり/なしの差分）。基準線 = 各カード単体（A のみ、B のみ）の最善手順。
    S = V(A,B) − V(A) − V(B) + V(なし)。因果の連鎖があり、全シードで S>0 なら combo（閾値は使わない。lift は順位付け用）。
    gain = 両方あるときと A のみのときの資源ベクトルの差（「手札+n、バトルゾーン+n」の形）を、シードの平均で返す。"""
    from dmsim.engine import scenario
    from ..search.game import play_game
    w = w or load_weights()

    def merge(*parts):
        out = {}
        for part in parts:
            for z, cards in (part or {}).items():
                out[z] = out.get(z, []) + list(cards)
        return out

    r = synergy(rules, a, b, base, opp=opp, w=w, turns=turns, seeds=seeds)
    vec = {}
    for k, p0 in {"a": merge(base, a), "ab": merge(base, a, b)}.items():
        acc = {x: 0.0 for x in RES}
        for sd in seeds:
            start = scenario.build(rules, {"p0": p0, "p1": opp or {}, "seed": sd})
            _, eng = play_game(rules, [], [], 1, max_turn=turns, start=start, lock_rounds=0, value_fn=lambda e, me: board_value(e, me, w))
            for x, v in resource_vector(eng, 0).items():
                acc[x] += v / len(seeds)
        vec[k] = acc
    gain = {x: round(vec["ab"][x] - vec["a"][x], 2) for x in RES}
    # 閾値は使わない。因果の連鎖（一方の効果が他方の誘発を起こした）と、全シードで S>0 の一貫性で判定する
    names = {c for part in (a, b) for cards in part.values() for c in cards}
    links = []
    for sd in seeds:
        _, _, lk, _ = traced_turn(rules, {"p0": merge(base, a, b), "p1": opp or {}, "seed": sd}, w, turns)
        links += [l for l in lk if l[0] in names and l[1] in names]
    links = sorted(set(links))
    consistent = all(x > 0 for x in r["per_seed"])
    gap = abs(r["mean"]["a"] - r["mean"]["none"]) + abs(r["mean"]["b"] - r["mean"]["none"])
    return {"S": r["S"], "per_seed": r["per_seed"], "causal_links": links, "consistent": consistent,
            "lift": r["S"] / gap if gap > 1e-9 else None, "is_combo": bool(links) and consistent,
            "gain_over_a": gain, "mean": r["mean"], "seeds": list(seeds)}


def causal_links(trace: list) -> list[tuple[str, str]]:
    """対戦の誘発ログから、カード間の因果の連鎖 (起こした側, 誘発した側) を返す。同じカード同士は除く。"""
    return sorted({(t["cause"], t["src"]) for t in trace if t.get("cause") and t["cause"] != t["src"]})


def traced_turn(rules, spec: dict, w: dict | None = None, turns: int = 1, budget: int = 200):
    """turn_value と同じだが、最善手順を選んだ後に再生して誘発の因果を記録する。(V, 資源ベクトル, 因果の連鎖, trace) を返す。"""
    from dmsim.engine import scenario
    from dmsim.eval import replay
    from ..search.game import play_game
    w = w or load_weights()
    start = scenario.build(rules, spec)
    _, eng = play_game(rules, [], [], 1, max_turn=turns, budget=budget, start=start, lock_rounds=0,
                       value_fn=lambda e, me: board_value(e, me, w))
    steps = replay.steps_of(eng)
    again = scenario.build(rules, spec)
    trace_on(again)
    for kind, keys, idx in steps:               # 選ばれた手順を、記録を入れて再生する
        d = again.advance()
        if d is None:
            break
        again.answer(list(idx))
    return board_value(eng, 0, w), resource_vector(eng, 0), causal_links(trace_of(again)), trace_of(again)


def detect_conversion(mean: dict) -> list[str]:
    """デメリット変換の検出。単体の V が「なし」より低いカード X（a か b）が、相手と組むと回収される: V(a,b) > V(相手単体)。
    戻り値は、デメリット側のカード（"a" / "b"）の一覧。"""
    out = []
    for x, other in (("a", "b"), ("b", "a")):
        if mean[x] < mean["none"] - 1e-9 and mean["ab"] > mean[other] + 1e-9:
            out.append(x)
    return out


def scan_pair_report(rules, a: str, b: str, base: dict | None = None, opp: dict | None = None, places=PLACES,
                     w: dict | None = None, turns: int = 1, seeds=(1, 2, 3)) -> dict:
    """置き場所ごとに combo_report を回し、成立する条件・失敗する条件・デメリット変換を分けて返す。
    - works: 因果の連鎖があり全シードで S>0 の置き場所（成立条件）
    - fails: S ≤ 0 または符号が割れた置き場所（失敗条件。捨てずに記録する）
    - converts: 「デメリット変換」。A 単体の V が「なし」より低く（または B 単体が低く）、組にすると回収されて S>0 のもの"""
    works, fails, converts = [], [], []
    for pa in places:
        for pb in places:
            r = combo_report(rules, {pa: [a]}, {pb: [b]}, base or {}, opp=opp, w=w, turns=turns, seeds=seeds)
            row = {"place_a": pa, "place_b": pb, "S": r["S"], "consistent": r["consistent"], "causal_links": r["causal_links"],
                   "lift": r["lift"], "mean": r["mean"]}
            (works if r["is_combo"] else fails).append(row)
            for who in detect_conversion(r["mean"]):
                converts.append({**row, "disadvantage_card": a if who == "a" else b,
                                 "solo_delta": r["mean"][who] - r["mean"]["none"]})
    return {"a": a, "b": b, "works": works, "fails": fails, "converts": converts}
