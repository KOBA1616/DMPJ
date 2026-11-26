#!/usr/bin/env python3
"""Phase 26-1: 等価手の集約の学習 A/B。

同一条件（土台 = Colab 11,200 局モデル、同一シード、25 iter × 12 局 = 300 局）
で集約 OFF / ON を学習し、対貪欲40局（seed=999）とミラー30局のループキル
（play_content、シード 40000+i、Phase 24 と同一条件）で比較する。
土台モデル自体の評価も同じ条件で併記する。
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("DMSIM_RUST", "0")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import evaluate, train_iters  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.game_content import play_content  # noqa: E402

BASE = "/home/hatch/workspace/phase21/model_colab_big.npz"
OUT = Path("/home/hatch/workspace/phase26")
ITERS, GAMES_PER_ITER, SEED, LR = 25, 12, 700, 3e-3


def report(name, rules, vocab, deck, model, aggregate):
    rows = [play_content(rules, vocab, deck, 40000 + i,
                         (("policy", model), ("policy", model)))
            for i in range(30)]
    rows = [r for r in rows if r]
    kills = sum(1 for r in rows if r["loop_own_turn"] is not None)
    det = [r["loop_own_turn"] for r in rows if r["loop_own_turn"] is not None]
    turns = sum(r["turns"] for r in rows) / len(rows)
    det_s = f"{sum(det) / len(det):.1f}" if det else "-"
    print(f"[{name}] ミラー30局: ループキル {kills}/30、初検出 {det_s}、"
          f"総ターン {turns:.1f}", flush=True)
    r = evaluate(rules, vocab, model, deck, deck, 40, seed=999,
                 opponent="greedy", aggregate=aggregate)
    print(f"[{name}] 対貪欲40局: {r['win_rate']:.2f}", flush=True)
    return kills, r["win_rate"]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")

    base = Model.load(BASE)
    report("土台(11,200局)", rules, vocab, deck, base, False)

    for name, agg in (("集約OFF", False), ("集約ON", True)):
        t0 = time.time()
        m = Model.load(BASE)
        train_iters(rules, vocab, m, deck, deck, ITERS, GAMES_PER_ITER,
                    seed=SEED, lr=LR, aggregate=agg,
                    log=lambda s: print(f"  [{name}] {s}", flush=True))
        out = OUT / f"model_agg_{'on' if agg else 'off'}.npz"
        m.save(str(out))
        print(f"[{name}] 学習 {time.time() - t0:.0f}s、保存 {out}", flush=True)
        report(name, rules, vocab, deck, m, agg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
