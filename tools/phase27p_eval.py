#!/usr/bin/env python3
"""Phase 27' の評価: 能力ブロック注意モデル（ゼロから2,000局）を
Phase 24〜26-4 と同一条件で測り、26-4 の ID／属性の数字と並べる。

主指標: ミラー30局（シード 40000+i）のループキル、対貪欲40局
（seed=999）、対探索プレイヤー（予算300）20局、loop_stages 診断
40局（到達・手順・出口）。

26-4 の記録（同一条件・ゼロから2,000局、docs/ai-phases.md）:
  ID:   ループキル 6/30、対貪欲 0.42、対探索 0.50、
        到達 0.57 / 手順 0.41 / 出口 0.32
  属性: ループキル 3/30、対貪欲 0.50、対探索 0.45、
        到達 0.61 / 手順 0.20 / 出口 0.30
仮説: 手順が属性版の 0.20 から回復するか（プーリングでは効果と
対象を結び付けられない、という仮説の検証）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model_abattn import AbAttnModel  # noqa: E402
from dmsim.ai.selfplay import evaluate  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.game_content import play_content  # noqa: E402
from tools.loop_stages import diagnose  # noqa: E402
from tools.phase26_eval import eval_vs_search  # noqa: E402

OUT = Path("/home/hatch/workspace/phase27p")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(OUT / "model_abattn.npz"))
    ap.add_argument("--skip-search", action="store_true")
    ap.add_argument("--skip-stages", action="store_true")
    a = ap.parse_args()
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    m = AbAttnModel.load(a.model, vocab, rules=rules)
    name = "能力ブロック注意(ゼロから2,000局)"
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
    if not a.skip_search:
        rs = eval_vs_search(rules, vocab, m, deck)
        print(f"[{name}] 対探索(予算300)20局: {rs['win_rate']:.2f}"
              f"（{rs['wins']}勝 {rs['losses']}敗 {rs['draws']}分）",
              flush=True)
    if not a.skip_stages:
        diagnose(rules, vocab, deck, m, games=40, label=name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
