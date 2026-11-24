#!/usr/bin/env python3
"""教材効果の判別力ある検証（Phase 15）。

Phase 11 の題材（ループ直前の局面）は未学習でも勝率が高く、教材の効果が
測れなかった。ここでは「仕込みが要る局面」（saga_prep_setup: 必要カードが
シャッフルされた山札の中、複数ターンかけて組み立てる）で測る。

設計:
- 教材は seed 0 の並びで教師（探索）が勝った1局から作る。
- 評価は seed 1〜7 の並び（教材と違う並び）で、汎化を見る。
- 学習は自己対戦のみ（対照）と 自己対戦＋教材 を同じ量で比べる。

使い方: python3 tools/demo_hard.py --iters 30
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

from dmsim.ai.demo import execution_rate, record_game_demo  # noqa: E402
from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import train_iters  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402


def prep_start(rules, spec, seed: int):
    s = dict(spec)
    s["seed"] = seed
    return sc.build(rules, s)


def exec_over_seeds(rules, vocab, model, spec, seeds, trials: int) -> float:
    rates = []
    for sd in seeds:
        start = prep_start(rules, spec, sd)
        rates.append(execution_rate(rules, vocab, model, start,
                                    trials=trials, seed=5000 + sd))
    return sum(rates) / len(rates)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", default="tests/saga_prep_setup.yaml")
    ap.add_argument("--iters", type=int, default=30)
    ap.add_argument("--games-per-iter", type=int, default=8)
    ap.add_argument("--trials", type=int, default=8)
    ap.add_argument("--budget", type=int, default=600)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    t0 = time.time()
    rules = load_rules()
    vocab = Vocab(rules)
    spec = yaml.safe_load(Path(args.setup).read_text(encoding="utf-8"))
    deck = load_deck("data/decks/saga.yaml")
    # 相手にも40枚の山札を持たせる（元の spec は相手の山札が12枚しかなく、
    # 相手が勝手に山札切れで負けて「勝ち」が水増しされるため）。
    # これで P0 の勝ちは、自分の山札が尽きる前に実際に倒した場合だけになる。
    spec["p1"] = {"deck": deck}
    # P0 の山札を 9 枚に絞り、制限時間を付ける（だらだら遊ぶと自滅する）。
    spec["deck_left"] = [9, None]
    eval_seeds = [1, 2, 3, 4, 5, 6, 7]

    fresh = Model(len(vocab), seed=args.seed)
    base = exec_over_seeds(rules, vocab, fresh, spec, eval_seeds, args.trials)
    print(f"未学習: 仕込み局面の実行率 {base:.2f}（seed 1-7 平均）")

    demo = record_game_demo(rules, vocab, prep_start(rules, spec, 0),
                            budget=args.budget)
    print(f"教材: {len(demo)} 決定（seed 0 の教師対局、{time.time() - t0:.0f}s）")

    results = {}
    for name, dm, rep in [("教材なし", None, 1), ("教材あり", demo, 1),
                          ("教材あり×10", demo, 10)]:
        m = Model(len(vocab), seed=args.seed)
        train_iters(rules, vocab, m, deck, deck, args.iters,
                    args.games_per_iter, seed=args.seed, demo=dm,
                    demo_repeat=rep, log=lambda h: None)
        r = exec_over_seeds(rules, vocab, m, spec, eval_seeds, args.trials)
        results[name] = r
        print(f"{name}: 実行率 {r:.2f}（{time.time() - t0:.0f}s）")
    print(f"教材の効果: {results['教材あり'] - results['教材なし']:+.2f} / "
          f"×10: {results['教材あり×10'] - results['教材なし']:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
