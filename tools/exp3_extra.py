#!/usr/bin/env python3
"""実験3の追加検証: 混合重みのスイープと top-2＋ε 枝刈り。

葉の混合（手作り評価 + w × 価値）で w を変えて勝ち筋探索を測る。
枝刈りは「方策の上位2つ + 残りから確率 ε で残す」変種を測る。

使い方: python3 tools/exp3_extra.py --model M
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import time
from pathlib import Path

os.environ.setdefault("DMSIM_RUST", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import yaml  # noqa: E402

from dmsim.ai.demo import policy_order_fn, state_value  # noqa: E402
from dmsim.ai.encode import Vocab, encode_state  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from dmsim.search.leaf_eval import Weights, evaluate  # noqa: E402
from dmsim.search.turn import TurnSearch  # noqa: E402

W = Weights()


def run_search(rules, spec, budget, value_fn=None, order_fn=None):
    eng = sc.build(rules, spec)
    ts = TurnSearch(0, budget, value_fn=value_fn, order_fn=order_fn)
    leaf, st = ts.run(eng)
    r = leaf.s.result
    won = r is not None and r.get("winner") == 0
    return won, st.nodes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    rules = load_rules()
    vocab = Vocab(rules)
    model = Model.load(args.model)
    spec = yaml.safe_load(
        Path("tests/saga_loop_first_setup.yaml").read_text(encoding="utf-8"))

    def s_value(eng, me):
        return state_value(model, encode_state(eng, me, vocab))

    def s_leaf(eng, me):
        return evaluate(eng, me, W) - evaluate(eng, 1 - me, W)

    print("混合重みのスイープ（予算 1500）:")
    for w in (75.0, 150.0, 300.0, 600.0):
        vf = lambda e, me, w=w: s_leaf(e, me) + w * s_value(e, me)
        t0 = time.time()
        won, nodes = run_search(rules, spec, 1500, value_fn=vf)
        print(f"  w={w:g}: {'発見' if won else '未発見'} / ノード {nodes}"
              f"（{time.time() - t0:.0f}s）")

    print("top-2＋ε 枝刈り（ε=0.2）:")
    base_order = policy_order_fn(model, vocab)

    def eps_order(eng, d, cands):
        ranked = base_order(eng, d, list(cands))
        rng = random.Random(12345)
        keep = list(ranked[:2])
        for c in ranked[2:]:
            if rng.random() < 0.2:
                keep.append(c)
        return keep

    for budget in (600, 1500):
        t0 = time.time()
        won, nodes = run_search(rules, spec, budget, order_fn=eps_order)
        print(f"  予算 {budget}: {'発見' if won else '未発見'} / "
              f"ノード {nodes}（{time.time() - t0:.0f}s）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
