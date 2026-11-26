#!/usr/bin/env python3
"""ループの4段階の分解測定: 取得・到達・手順・出口。

入口条件（data/loops/entry/saga.json の minimal）を盤面で評価し、
対戦中の各プレイヤーについて次を追う。
  取得: 各条件を満たしたことがあるか（部品集めの進捗）
  到達: 全条件を同時に満たした（= 最小盤面 M に到達した）か、何ターン目か
  手順: 到達後にループが検出されたか
  出口: ループ検出後に勝ったか / 到達したがループ無しで勝ったか
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import model_policy  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.engine.loop import LoopDetector  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.game_content import own_turn  # noqa: E402

MINIMAL = json.loads(
    (Path(__file__).resolve().parents[1]
     / "data/loops/entry/saga.json").read_text())["minimal"]


def condition_counts(eng, rules, player: int) -> list[int]:
    """minimal の各条件について、現在の充足数（n と比べる前の実数）を返す。"""
    out = []
    for cond in MINIMAL:
        zones = cond["zones"] if cond["zones"] else [cond["zone"]]
        match = cond["match"]
        cnt = 0
        for z in zones:
            for cid in eng.s.zones[z][player]:
                defn = eng.s.cards[cid].defn
                cdef = rules.cards[defn]
                if "name" in match and defn != match["name"]:
                    continue
                if "types" in match and not set(match["types"]) & set(cdef.types):
                    continue
                if "civs" in match and not set(match["civs"]) & set(cdef.civs):
                    continue
                cnt += 1
        out.append(cnt)
    return out


def reached_M(eng, rules, player: int) -> bool:
    counts = condition_counts(eng, rules, player)
    return all(c >= cond["n"] for c, cond in zip(counts, MINIMAL))


def analyze_game(rules, vocab, deck, model, seed: int) -> dict:
    """ミラー1局を4段階で分析する（両プレイヤー分を返す）。"""
    first = seed % 2
    eng = Engine.new_game(rules, [deck, deck], seed, first_player=first)
    pols = {p: model_policy(model, vocab,
                            np.random.default_rng(seed * 31 + p))
            for p in (0, 1)}
    dets = {p: LoopDetector(me=p, report_all=True) for p in (0, 1)}
    info = {p: {"cond_ever": [False] * len(MINIMAL), "reach_turn": None,
                "loop_turn": None} for p in (0, 1)}
    for _ in range(500):
        if eng.s.result is not None:
            break
        d = eng.advance()
        if d is None:
            break
        p = d["player"]
        eng.answer(pols[p](eng, d))
        for q in (0, 1):
            counts = condition_counts(eng, rules, q)
            for i, (c, cond) in enumerate(zip(counts, MINIMAL)):
                if c >= cond["n"]:
                    info[q]["cond_ever"][i] = True
            if info[q]["reach_turn"] is None and all(
                    c >= cond["n"] for c, cond in zip(counts, MINIMAL)):
                info[q]["reach_turn"] = own_turn(eng.s.turn, q, first)
            if info[q]["loop_turn"] is None and dets[q].observe(eng):
                info[q]["loop_turn"] = own_turn(eng.s.turn, q, first)
    res = eng.s.result
    w = res.get("winner") if res else None
    for q in (0, 1):
        info[q]["won"] = (w == q)
    return info


def diagnose(rules, vocab, deck, model, games: int = 40, seed0: int = 40000,
             label: str = "") -> dict:
    samples = []
    for i in range(games):
        info = analyze_game(rules, vocab, deck, model, seed0 + i)
        samples.extend(info.values())
    n = len(samples)
    reached = [s for s in samples if s["reach_turn"] is not None]
    looped = [s for s in reached if s["loop_turn"] is not None]
    cond_rates = [sum(1 for s in samples if s["cond_ever"][i]) / n
                  for i in range(len(MINIMAL))]
    stats = {
        "n": n,
        "cond_rates": cond_rates,
        "reach_rate": len(reached) / n,
        "reach_turn_avg": (sum(s["reach_turn"] for s in reached)
                           / len(reached) if reached else None),
        "loop_given_reach": len(looped) / len(reached) if reached else None,
        "win_given_loop": (sum(1 for s in looped if s["won"]) / len(looped)
                           if looped else None),
        "win_given_reach_noloop": (
            sum(1 for s in reached if s["loop_turn"] is None and s["won"])
            / max(1, sum(1 for s in reached if s["loop_turn"] is None))),
        "win_given_noreach": (
            sum(1 for s in samples if s["reach_turn"] is None and s["won"])
            / max(1, sum(1 for s in samples if s["reach_turn"] is None))),
    }
    print(f"[{label}] サンプル {n}（{games} 局 × 両座席）")
    print(f"  取得（条件別の充足率）: "
          + " ".join(f"{r:.2f}" for r in cond_rates))
    rt = stats["reach_turn_avg"]
    print(f"  到達率: {stats['reach_rate']:.2f}"
          f"（平均 {rt:.1f} 自ターン目）" if rt else
          f"  到達率: {stats['reach_rate']:.2f}")
    print(f"  手順（到達→ループ検出）: {stats['loop_given_reach']}")
    print(f"  出口（ループ→勝利）: {stats['win_given_loop']} / "
          f"到達・ループ無しでの勝利: {stats['win_given_reach_noloop']:.2f} / "
          f"未到達での勝利: {stats['win_given_noreach']:.2f}")
    return stats


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    m = Model.load(a.model)
    diagnose(rules, vocab, deck, m, games=a.games,
             label=a.label or a.model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
