#!/usr/bin/env python3
"""等価な合法手の重複率の測定（実験4、測定のみ）。

各決定の選択肢にはエンジンが意味キー（option の "key"）を付けている。
同じキーを持つ選択肢は、エンジン自身の再生機構が「同じ手」とみなすもの。
自己対戦の局面で、重複を含む決定がどれくらいあるかを数える。

使い方: python3 tools/dup_rate.py --games 20 [--model PATH]
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

os.environ.setdefault("DMSIM_RUST", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np  # noqa: E402

from dmsim.ai.demo import model_policy  # noqa: E402
from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.engine.play import random_policy  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402


def measure(rules, deck, policy_fn, games: int, seed: int):
    stats = Counter()
    by_kind = {}
    for g in range(games):
        eng = Engine.new_game(rules, [deck, deck], seed + g, first_player=g % 2)
        pols = [policy_fn(), policy_fn()]
        for _ in range(4000):
            d = eng.advance()
            if d is None:
                break
            keys = [o["key"] for o in d["options"]]
            n, u = len(keys), len(set(keys))
            stats["decisions"] += 1
            stats["options"] += n
            stats["distinct"] += u
            if u < n:
                stats["dup_decisions"] += 1
            k = by_kind.setdefault(d["kind"], Counter())
            k["decisions"] += 1
            k["options"] += n
            k["distinct"] += u
            if u < n:
                k["dup_decisions"] += 1
            eng.answer(pols[d["player"]](eng, d))
    return stats, by_kind


def show(name, stats, by_kind):
    dec = stats["decisions"]
    print(f"{name}: 決定 {dec} 件、重複を含む決定 "
          f"{stats['dup_decisions']} 件（{stats['dup_decisions'] / dec:.1%}）、"
          f"選択肢 {stats['options']} 個 → 等価でないもの {stats['distinct']} 個"
          f"（重複 {1 - stats['distinct'] / stats['options']:.1%}）")
    top = sorted(by_kind.items(),
                 key=lambda kv: kv[1]["options"] - kv[1]["distinct"],
                 reverse=True)[:5]
    for kind, k in top:
        dup = k["options"] - k["distinct"]
        if dup:
            print(f"  {kind}: 決定 {k['decisions']} 件、重複選択肢 {dup} 個")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--model", default=None)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    t0 = time.time()
    rules = load_rules()
    deck = load_deck("data/decks/saga.yaml")

    rng = random.Random(args.seed)
    s, bk = measure(rules, deck, lambda: random_policy(rng), args.games,
                    args.seed)
    show("ランダム方策", s, bk)

    if args.model:
        vocab = Vocab(rules)
        model = Model.load(args.model)
        s, bk = measure(
            rules, deck,
            lambda: model_policy(model, vocab,
                                 np.random.default_rng(rng.randrange(1 << 30))),
            args.games, args.seed)
        show("学習済み方策", s, bk)
    print(f"合計 {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
