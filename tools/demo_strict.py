#!/usr/bin/env python3
"""教材効果の厳格化した検証（実験1）。

Phase 11 の題材（ループ直前の局面）は「勝てば成功」で数えたため、ループを
回さない直接勝ちでも成功になり、教材の効果が測れなかった。ここでは成功を
「実際にループを回して勝つこと」に限定する。ループの検出にはエンジン自身の
LoopDetector（同じ盤面の骨格への回帰）を使う。

教材は Phase 11 のキャッシュ（demo_cache_loop.pkl、ループ区間を含む46決定）
を再利用する。評価は未学習／自己対戦のみ／自己対戦＋教材の3条件。

使い方: python3 tools/demo_strict.py --iters 30 --trials 16
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
import numpy as np  # noqa: E402
import yaml  # noqa: E402

from dmsim.ai.demo import model_policy  # noqa: E402
from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import train_iters  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from dmsim.engine.loop import LoopDetector  # noqa: E402
from dmsim.search.turn import charge_only_policy  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402


def play_strict(vocab, model, start_eng, rng, me: int = 0):
    """1局指し、(勝ち, ループを回したか) を返す。"""
    eng = start_eng.clone()
    det = LoopDetector(me=me, report_all=True)
    pol = model_policy(model, vocab, rng)
    looped = False
    for _ in range(2000):
        d = eng.advance()
        if d is None:
            break
        if d["player"] == me:
            eng.answer(pol(eng, d))
            if det.observe(eng) is not None:
                looped = True
        else:
            eng.answer(charge_only_policy(eng, d))
    res = eng.s.result
    return bool(res and res.get("winner") == me), looped


def strict_rate(vocab, model, start_eng, trials: int, seed: int):
    wins = strict = 0
    for t in range(trials):
        w, looped = play_strict(vocab, model, start_eng,
                                np.random.default_rng(seed + t))
        wins += w
        strict += w and looped
    return wins / trials, strict / trials


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", default="tests/saga_loop_first_setup.yaml")
    ap.add_argument("--demo-cache",
                    default=str(Path.home() /
                                "workspace/demo_phase11/demo_cache_loop.pkl"))
    ap.add_argument("--iters", type=int, default=30)
    ap.add_argument("--games-per-iter", type=int, default=8)
    ap.add_argument("--trials", type=int, default=16)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    t0 = time.time()
    rules = load_rules()
    vocab = Vocab(rules)
    spec = yaml.safe_load(Path(args.setup).read_text(encoding="utf-8"))
    start = sc.build(rules, spec)
    deck = load_deck("data/decks/saga.yaml")
    demo = pickle.loads(Path(args.demo_cache).read_bytes())
    print(f"教材: {len(demo)} 決定（キャッシュ再利用）")

    arms = [("未学習", None, False), ("教材なし", None, True),
            ("教材あり", demo, True)]
    for name, dm, train in arms:
        m = Model(len(vocab), seed=args.seed)
        if train:
            train_iters(rules, vocab, m, deck, deck, args.iters,
                        args.games_per_iter, seed=args.seed, demo=dm,
                        log=lambda h: None)
        w, s = strict_rate(vocab, m, start, args.trials, 7000)
        print(f"{name}: 勝率 {w:.2f} / ループ実行率 {s:.2f}"
              f"（{time.time() - t0:.0f}s）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
