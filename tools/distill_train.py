#!/usr/bin/env python3
"""蒸留データでモデルを微調整する（Phase 17）。

item の ret は探索由来の評価（-1..1）なので、既存の学習器に流すと
価値ヘッドは「探索の評価」を、方策は「探索の選んだ手」を学ぶ。

使い方: python3 tools/distill_train.py --model M --data distill.pkl --out OUT
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

from dmsim.ai.model import Model  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--lr", type=float, default=1e-3)
    args = ap.parse_args()

    t0 = time.time()
    model = Model.load(args.model)
    items = pickle.loads(Path(args.data).read_bytes())
    print(f"蒸留データ {len(items)} 件で {args.epochs} エポック微調整")
    for ep in range(args.epochs):
        loss, grads = model.loss_and_grads(items)
        model.step(grads, lr=args.lr)
        if ep % 10 == 0 or ep == args.epochs - 1:
            print(f"  epoch {ep}: loss {loss:.3f}（{time.time() - t0:.0f}s）")
    model.save(args.out)
    print(f"保存: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
