#!/usr/bin/env python3
"""方策による候補の並べ替え・枝刈りの検証（Phase 12）。

サガループ局面の TurnSearch で、予算を絞った時に「勝ち筋を発見できるか」と
「使うノード数」を、従来の並び／方策の並べ替え／方策＋上位 cap 個への
枝刈りで比べる。並べ替えだけなら完全性は保たれ、枝刈りは速さと引き換えに
見落としの危険がある——その境目を数字で見る。

使い方: python3 tools/policy_order_compare.py --model model.npz
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("DMSIM_RUST", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import yaml  # noqa: E402

from dmsim.ai.demo import policy_order_fn  # noqa: E402
from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from dmsim.search.turn import TurnSearch  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--budgets", default="150,300,600,1500")
    args = ap.parse_args()

    rules = load_rules()
    vocab = Vocab(rules)
    model = Model.load(args.model)
    spec = yaml.safe_load(
        Path("tests/saga_loop_first_setup.yaml").read_text(encoding="utf-8"))
    variants = [
        ("従来の並び", None),
        ("方策の並べ替え", policy_order_fn(model, vocab)),
        ("方策＋上位2つに枝刈り", policy_order_fn(model, vocab, cap=2)),
        ("方策＋上位1つに枝刈り", policy_order_fn(model, vocab, cap=1)),
    ]
    for budget in [int(x) for x in args.budgets.split(",")]:
        for name, ofn in variants:
            eng = sc.build(rules, spec)
            t0 = time.time()
            ts = TurnSearch(0, budget, order_fn=ofn)
            leaf, st = ts.run(eng)
            r = leaf.s.result
            won = r is not None and r.get("winner") == 0
            print(f"予算 {budget:>5} / {name}: "
                  f"{'勝ち筋 発見' if won else '未発見'}"
                  f" / ノード {st.nodes} / {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
