#!/usr/bin/env python3
"""探索を学習に畳み込む方式の対戦検証（Phase 19）。

探索なしで指す蒸留方策が、探索プレイヤーの強さにどこまで近づけたか。
- 蒸留方策 vs 貪欲 / 本番モデル vs 貪欲（evaluate、学習信号の差の対照）
- 探索プレイヤー vs 貪欲（先生の強さ＝天井）
- 蒸留方策 vs 探索プレイヤー（直接対決）
- サガループ局面の実行率（蒸留前後）

使い方: python3 tools/fold_compare.py --distilled M2 --base M0
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("DMSIM_RUST", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np  # noqa: E402
import yaml  # noqa: E402

from dmsim.ai.demo import execution_rate, greedy_policy, model_policy  # noqa: E402
from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import evaluate  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.search.turn import TurnSearch  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402


def play_match(rules, vocab, deck, seed: int, sides, budget: int = 400):
    """sides: 各プレイヤーが ("policy", model) / ("search",) / ("greedy",)。"""
    eng = Engine.new_game(rules, [deck, deck], seed, first_player=seed % 2)
    greedy = greedy_policy()
    pols = {}
    for i, side in enumerate(sides):
        if side[0] == "policy":
            pols[i] = model_policy(side[1], vocab,
                                   np.random.default_rng(seed * 31 + i))
        else:
            pols[i] = greedy
    for _ in range(120):
        if eng.s.result is not None:
            break
        me = eng.s.active
        if sides[me][0] == "search":
            ts = TurnSearch(me, budget, opp_policy=greedy)
            eng, _st = ts.run(eng)
            while eng.s.result is None and eng.s.active != me:
                d = eng.advance()
                if d is None:
                    break
                eng.answer(pols[d["player"]](eng, d))
        else:
            cur = me
            while eng.s.result is None and eng.s.active == cur:
                d = eng.advance()
                if d is None:
                    break
                eng.answer(pols[d["player"]](eng, d))
    res = eng.s.result
    return None if not res else res.get("winner")


def match_rate(rules, vocab, deck, sides, games: int, seed: int):
    wins = played = 0
    for i in range(games):
        w = play_match(rules, vocab, deck, seed + i, sides)
        if w is not None:
            played += 1
            wins += w == 0
    return wins, played


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--distilled", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--games", type=int, default=8)
    ap.add_argument("--eval-games", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    t0 = time.time()
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    distilled = Model.load(args.distilled)
    base = Model.load(args.base)

    for name, m in [("本番モデル（対照）", base), ("蒸留方策", distilled)]:
        r = evaluate(rules, vocab, m, deck, deck, args.eval_games,
                     seed=1000, opponent="greedy")
        print(f"{name} vs 貪欲: 勝率 {r['win_rate']:.2f}"
              f"（{time.time() - t0:.0f}s）")

    w, n = match_rate(rules, vocab, deck, [("search",), ("greedy",)],
                      args.games, args.seed + 500)
    print(f"探索プレイヤー vs 貪欲: P0 勝率 {w / max(1, n):.2f}（{w}/{n} 局、"
          f"{time.time() - t0:.0f}s）")

    w, n = match_rate(rules, vocab, deck,
                      [("policy", distilled), ("search",)],
                      args.games, args.seed + 900)
    print(f"蒸留方策 vs 探索プレイヤー: P0 勝率 {w / max(1, n):.2f}"
          f"（{w}/{n} 局、{time.time() - t0:.0f}s）")

    spec = yaml.safe_load(
        Path("tests/saga_loop_first_setup.yaml").read_text(encoding="utf-8"))
    start = sc.build(rules, spec)
    for name, m in [("本番モデル", base), ("蒸留方策", distilled)]:
        r = execution_rate(rules, vocab, m, start, trials=16, seed=3000)
        print(f"ループ実行率 {name}: {r:.2f}（{time.time() - t0:.0f}s）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
