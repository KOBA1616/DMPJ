#!/usr/bin/env python3
"""Colab 用の大規模学習（中断耐性つき）。

50 iter（800 局）ごとに Google Drive 上のチェックポイントへ保存し、
そこから再開する。Colab のセッションが切れても最大1ブロック分しか
失われず、再実行すれば続きから学習できる。

使い方（Colab 内）: python tools/colab_big_train.py [--blocks 10]
前提: /content/DMPJ に cd 済み。Drive の model_colab_newdeck.npz
（3,200 局学習済み）を初期チェックポイントとして引き継ぐ。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time

CKPT = "/content/drive/MyDrive/model_colab_big.npz"
SRC = "/content/drive/MyDrive/model_colab_newdeck.npz"


def ensure_drive() -> None:
    if os.path.exists("/content/drive/MyDrive"):
        return
    from google.colab import drive  # Colab 内でのみ import できる
    drive.mount("/content/drive")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", type=int, default=10)
    ap.add_argument("--iters", type=int, default=50)
    ap.add_argument("--games-per-iter", type=int, default=16)
    args = ap.parse_args()

    ensure_drive()
    if not os.path.exists(CKPT):
        shutil.copy(SRC, CKPT)
        print(f"checkpoint を初期化: {SRC} -> {CKPT}", flush=True)
    env = {**os.environ, "DMSIM_RUST": "0"}
    t0 = time.time()
    for b in range(args.blocks):
        print(f"=== block {b + 1}/{args.blocks} "
              f"({time.time() - t0:.0f}s) ===", flush=True)
        r = subprocess.run(
            [sys.executable, "tools/selfplay_train.py", "--model", "torch",
             "--deck", "data/decks/saga.yaml",
             "--iters", str(args.iters),
             "--games-per-iter", str(args.games_per_iter),
             "--eval-games", "20", "--opponents", "random,greedy",
             "--workers", "2", "--init", CKPT, "--out", CKPT],
            env=env)
        print(f"block {b + 1} rc={r.returncode} "
              f"({time.time() - t0:.0f}s)", flush=True)
        if r.returncode != 0:
            return r.returncode
    print(f"全ブロック完了（{time.time() - t0:.0f}s）", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
