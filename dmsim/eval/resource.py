"""リソース型の目盛り（S4、docs/combo-ruler-design.md §6 タスク12・§11）。ループ型の段1・段2とは別の欄。

測るもの: 入口の局面から自分の1ターンを探索に指させ、使ったマナと札に対して得た札と場の量。
- 局面: 入口に要る札（setup の p0 の hand・graveyard・bz・mana）はそのまま、手札の残り（hand_fill 枚）・盾5枚・山札はデッキの残りをシードで配る。
- 前後の差: 手札 Δhand・場 Δboard・盾 Δshield（相手の分は数えない）。
- 使った量: タップしたマナ mana_used、手札から出ていった札 cards_spent（=手札が減った分ではなく、手札から他のゾーンへ動いた枚数）。
- 得た量 gain = 手札に入った枚数 + Δboard + Δshield（入った枚数は Δhand + cards_spent）。
- 効率 adv = gain / (mana_used + cards_spent)、分母0なら gain。
合格線は置かない（既知とランダム組の分布を出すだけ。線は指揮役とユーザーが決める）。
cost_perf（V の順位づけ用の加点）とは別: こちらは物差しの記録で、重みを掛けない生の数。
"""
from __future__ import annotations

import json
import random
import statistics

from ..base.store import REPO


def _deal(spec: dict, deck: list[str], seed: int) -> dict:
    p0 = {k: list(v) for k, v in spec["p0"].items()}
    rest = list(deck)
    for ids in p0.values():
        for i in ids:
            if i in rest:
                rest.remove(i)
    rng = random.Random(seed)
    rng.shuffle(rest)
    k = int(spec.get("hand_fill", 0))
    p0["hand"] = p0.get("hand", []) + rest[:k]
    p0["shield"] = rest[k:k + 5]
    p0["deck"] = rest[k + 5:]
    return {"p0": p0, "p1": spec.get("p1", {}), "deck_exact": [True, False], "deck_size": spec.get("opp_deck", 30), "seed": seed}


def _counts(eng, me=0) -> dict:
    from ..engine.view import tapped_of, zone_of
    return {"hand": len(zone_of(eng, "hand", me)), "board": len(eng.bz_tops(me)), "shield": len(zone_of(eng, "shield", me)),
            "tapped": sum(1 for c in zone_of(eng, "mana", me) if tapped_of(eng, c))}


def measure_one(rules, spec: dict, deck: list[str], seed: int, budget: int = 200) -> dict:
    from ..engine import scenario
    from ..search.game import play_game
    from .ruler_control import start_key
    e = scenario.build(rules, _deal(spec, deck, seed), first_player=0)
    key = start_key(e)
    holder = {}

    def hook(eng, me, rounds):      # 自分の1ターン目の後（ロック判定の位置）に局面を写す
        holder.setdefault("after", (eng.clone(), _counts(eng, me)))
        return None
    before = _counts(e)
    res, eng = play_game(rules, deck, [], seed, first_player=0, max_turn=1, budget=budget, start=e, lock_judge=hook)
    after_eng, after = holder.get("after", (eng, _counts(eng)))
    spent = sum(1 for x in after_eng.log if x["kind"] in ("main", "charge", "discard", "choose_cards")
                and any(k.startswith(("play:", "charge:")) for k in x["keys"]))
    d = {k: after[k] - before[k] for k in ("hand", "board", "shield")}
    used = after["tapped"] - before["tapped"]
    gain = (d["hand"] + spent) + d["board"] + d["shield"]
    den = used + spent
    return {"seed": seed, "start": key, "mana_used": used, "cards_spent": spent, **{f"d_{k}": v for k, v in d.items()},
            "gain": gain, "adv": round(gain / den, 3) if den else float(gain), "error": res.error}


def summarize(rows: list[dict]) -> dict:
    a = [r["adv"] for r in rows]
    g = [r["gain"] for r in rows]
    return {"n": len(rows), "adv_median": statistics.median(a) if a else None, "adv_min": min(a, default=None), "adv_max": max(a, default=None),
            "gain_median": statistics.median(g) if g else None}


def load_setup(path: str) -> tuple[dict, list[str]]:
    import yaml
    spec = json.loads((REPO / path).read_text(encoding="utf-8"))
    deck = yaml.safe_load((REPO / spec["deck"]).read_text(encoding="utf-8"))["deck"]
    return spec, deck


def swap(spec: dict, deck: list[str], old: str, new: str) -> tuple[dict, list[str]]:
    s = json.loads(json.dumps(spec))
    s["p0"] = {z: [new if i == old else i for i in ids] for z, ids in s["p0"].items()}
    return s, [new if i == old else i for i in deck]
