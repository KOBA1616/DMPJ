#!/usr/bin/env python3
"""方策蒸留の正しい方式（Phase 18）: BC＋自己対戦混合で1ラウンド回す。

Phase 17 の失敗（REINFORCE 微調整・300件×30エポックで方策が悪化）を踏まえ、
- 方策の学習は模倣専用の BC 損失（bc_loss_and_grads）で行う
- 自己対戦データ（現方策の対戦、REINFORCE）を混ぜて分布の崩れを防ぐ
- エポックは少なく（既定4）、学習率も小さめ
を守る。ラウンドを重ねる expert iteration の1回分。

使い方: python3 tools/distill_bc_train.py --model M --data D --out OUT \
            --selfplay-games 120 --epochs 4
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import time
from pathlib import Path

os.environ.setdefault("DMSIM_RUST", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import collect_games  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--selfplay-games", type=int, default=120)
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    t0 = time.time()
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    model = Model.load(args.model)
    distill = pickle.loads(Path(args.data).read_bytes())
    print(f"蒸留データ {len(distill)} 件")

    sp, _winners = collect_games(rules, vocab, model, deck, deck,
                                 args.selfplay_games, seed=args.seed + 777)
    print(f"自己対戦データ {len(sp)} 件（{time.time() - t0:.0f}s）")

    for ep in range(args.epochs):
        _l1, g1 = model.bc_loss_and_grads(distill)
        model.step(g1, lr=args.lr)
        _l2, g2 = model.loss_and_grads(sp)
        model.step(g2, lr=args.lr)
        print(f"  epoch {ep}: bc {_l1:.3f} / reinforce {_l2:.3f}"
              f"（{time.time() - t0:.0f}s）")
    model.save(args.out)
    print(f"保存: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
