#!/usr/bin/env python3
"""大規模学習モデル（累計11,200局）の内容と強さを 3,200 局モデルと比較する。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dmsim.ai.encode import Vocab            # noqa: E402
from dmsim.ai.model import Model             # noqa: E402
from dmsim.ai.selfplay import evaluate       # noqa: E402
from dmsim.cards.defs import load_rules      # noqa: E402
from tools.bench_2p import load_deck         # noqa: E402
from tools.game_content import play_content, summarize  # noqa: E402

MODELS = {
    "3,200局モデル": "/home/hatch/workspace/phase21/model_colab_newdeck.npz",
    "11,200局モデル": "/home/hatch/workspace/phase21/model_colab_big.npz",
}


def main() -> int:
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    for name, path in MODELS.items():
        m = Model.load(path)
        rows = [play_content(rules, vocab, deck, 40000 + i,
                             (("policy", m), ("policy", m)))
                for i in range(30)]
        summarize(f"{name} ミラー", rows)
        for opp in ("greedy", "random"):
            r = evaluate(rules, vocab, m, deck, deck, 40, seed=999,
                         opponent=opp)
            print(f"[{name}] 対{opp} 40局: {r['win_rate']:.2f} "
                  f"({r['wins']}W/{r['losses']}L/{r['draws']}D)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
