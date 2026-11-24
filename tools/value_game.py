#!/usr/bin/env python3
"""価値のゲームレベル利用（Phase 16）。

Phase 12 では「価値ヘッドを探索の葉にすると勝ち筋を見逃す」だったが、
あれは1ターン内の細かい誘導の話。ここでは通常の対戦（サガミラー）で、
ターン探索の葉を (a) 手作り評価 (b) 価値ヘッド (c) 混合 に替えて
フルゲームを指し、P0 の勝率を比べる。

両者とも自分のターンは TurnSearch で指し、相手ターン中の反応的な
決定は貪欲方策に任せる（条件は両条件で同じ）。

使い方: python3 tools/value_game.py --model M --seeds 6 --budget 400
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("DMSIM_RUST", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim.ai.demo import greedy_policy, state_value  # noqa: E402
from dmsim.ai.encode import Vocab, encode_state  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.search.leaf_eval import Weights, evaluate  # noqa: E402
from dmsim.search.turn import TurnSearch  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402

W = Weights()


def play_full(rules, deck, seed: int, vf0, budget: int):
    """P0 の葉だけ vf0（None=手作り）にし、P1 は手作り葉で指すフルゲーム。"""
    eng = Engine.new_game(rules, [deck, deck], seed, first_player=seed % 2)
    greedy = greedy_policy()
    for _ in range(80):
        if eng.s.result is not None:
            break
        me = eng.s.active
        vf = vf0 if me == 0 else None
        ts = TurnSearch(me, budget, opp_policy=greedy, value_fn=vf)
        eng, _st = ts.run(eng)
        while eng.s.result is None and eng.s.active != me:
            d = eng.advance()
            if d is None:
                break
            eng.answer(greedy(eng, d))
    res = eng.s.result
    return None if not res else res.get("winner")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--budget", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    t0 = time.time()
    rules = load_rules()
    vocab = Vocab(rules)
    model = Model.load(args.model)
    deck = load_deck("data/decks/saga.yaml")

    def v_value(eng, me):
        return state_value(model, encode_state(eng, me, vocab)) * 300.0

    def v_blend(eng, me):
        return v_value(eng, me) + evaluate(eng, me, W)

    arms = [("手作り葉（基準）", None), ("価値の葉", v_value),
            ("混合の葉", v_blend)]
    base = None
    for name, vf in arms:
        wins = 0
        played = 0
        for i in range(args.seeds):
            w = play_full(rules, deck, args.seed + 100 + i, vf, args.budget)
            if w is not None:
                played += 1
                wins += w == 0
        rate = wins / played if played else 0.0
        if base is None:
            base = rate
        print(f"{name}: P0 勝率 {rate:.2f}（{wins}/{played} 局、"
              f"{time.time() - t0:.0f}s）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
