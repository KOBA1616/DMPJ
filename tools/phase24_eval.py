#!/usr/bin/env python3
"""Phase 24 の総合評価: 土台と A/C/AC/B を同一条件で比較。

指標: ミラー30局（シード 40000+i、Phase 23 と同一）のループキル数と
初検出の自ターン、対貪欲40局の勝率。4段階診断は tools/loop_stages.py
を別途 --games 40 で回す。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import evaluate  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.game_content import play_content  # noqa: E402

P24 = "/home/hatch/workspace/phase24"
MODELS = {
    "土台(11,200局)": "/home/hatch/workspace/phase21/model_colab_big.npz",
    "A 到達ボーナス": f"{P24}/model_a.npz",
    "C 探索相手": f"{P24}/model_c.npz",
    "AC 両方": f"{P24}/model_ac.npz",
    "B 蒸留r1": f"{P24}/model_b_r1.npz",
    "B 蒸留r2": f"{P24}/model_b_r2.npz",
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
        rows = [r for r in rows if r]
        kills = sum(1 for r in rows if r["loop_own_turn"] is not None)
        det = [r["loop_own_turn"] for r in rows
               if r["loop_own_turn"] is not None]
        turns = sum(r["turns"] for r in rows) / len(rows)
        det_s = f"{sum(det) / len(det):.1f}" if det else "-"
        print(f"[{name}] ミラー30局: ループキル {kills}/30、"
              f"初検出 {det_s}、総ターン {turns:.1f}", flush=True)
        r = evaluate(rules, vocab, m, deck, deck, 40, seed=999,
                     opponent="greedy")
        print(f"[{name}] 対貪欲40局: {r['win_rate']:.2f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
