#!/usr/bin/env python3
"""大局観の校正と可視化（Phase 13）。

学習した価値ヘッドについて3つを測る。
1. 校正: 予測した勝率（価値 -1..1 → 0..1）と実際の勝率がどれだけ一致するか
   （予測の区間ごとに集計）。
2. カード評価: 対戦コーパスで「そのカードが自分の場・手札にある局面」の
   実際の勝率と平均価値（デッキ構築への応用の入口）。
3. 局面の説明: 指定局面で、場のカードを1枚ずつ抜いた時の価値の変化
   （どのカードを価値が重視しているか）。

使い方: python3 tools/value_report.py --model model.npz --games 40
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("DMSIM_RUST", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import yaml  # noqa: E402

from dmsim.ai.demo import state_value  # noqa: E402
from dmsim.ai.encode import Vocab, encode_state  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.leaf_compare import collect_positions  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--deck", default="data/decks/saga.yaml")
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    t0 = time.time()
    rules = load_rules()
    vocab = Vocab(rules)
    model = Model.load(args.model)
    deck = load_deck(args.deck)
    positions = collect_positions(rules, deck, deck, args.games, args.seed + 5)
    print(f"局面コーパス: {len(positions)} 局面（{args.games} 局）")

    # 1. 校正: 予測勝率の区間ごとの実勝率
    bins: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    card_stat: dict[str, list] = defaultdict(lambda: [0, 0, 0.0])
    for eng, winner in positions:
        for me in (0, 1):
            v = state_value(model, encode_state(eng, me, vocab))
            pred = (v + 1) / 2
            b = min(9, int(pred * 10))
            bins[b][0] += 1
            bins[b][1] += 1 if winner == me else 0
            seen = set()
            for z in ("bz", "hand", "mana"):
                for cid in eng.s.zones[z][me]:
                    seen.add(eng.s.cards[cid].defn)
            for dn in seen:
                card_stat[dn][0] += 1
                card_stat[dn][1] += 1 if winner == me else 0
                card_stat[dn][2] += v
    print("\n校正（予測勝率の区間 → 実際の勝率）:")
    for b in sorted(bins):
        n, w = bins[b]
        print(f"  {b / 10:.1f}〜{b / 10 + 0.1:.1f}: 実勝率 {w / n:.2f}（{n} 局面）")

    # 2. カード評価（出現30回以上）
    rows = [(dn, n, w / n, v / n) for dn, (n, w, v) in card_stat.items()
            if n >= 30]
    rows.sort(key=lambda r: -r[2])
    print("\nカード評価（そのカードが場・手札・マナにある局面の実勝率）:")
    for dn, n, wr, mv in rows[:5]:
        print(f"  上位 {dn}: 勝率 {wr:.2f} / 平均価値 {mv:+.2f}（{n} 局面）")
    for dn, n, wr, mv in rows[-3:]:
        print(f"  下位 {dn}: 勝率 {wr:.2f} / 平均価値 {mv:+.2f}（{n} 局面）")

    # 3. 局面の説明: サガループ局面で場のカードを1枚抜いた時の価値変化
    spec = yaml.safe_load(
        Path("tests/saga_loop_first_setup.yaml").read_text(encoding="utf-8"))
    eng = sc.build(rules, spec)
    eng.advance()
    base = state_value(model, encode_state(eng, 0, vocab))
    print(f"\nサガループ局面の価値（P0視点）: {base:+.2f}")
    impacts = []
    for z in ("bz", "graveyard", "mana", "hand"):
        for cid in list(eng.s.zones[z][0]):
            e2 = eng.clone()
            card = e2.s.cards[cid]
            e2.s.zones[z][0].remove(cid)
            e2.s.zones["deck"][0].append(cid)   # 山札に戻して「場から消す」
            card.zone = "deck"
            v2 = state_value(model, encode_state(e2, 0, vocab))
            impacts.append((base - v2, card.defn, z))
    impacts.sort(reverse=True)
    print("抜くと価値が最も下がるカード（＝価値が重視しているカード）:")
    for dv, dn, z in impacts[:5]:
        print(f"  {dn}（{z}）: 価値 {dv:+.2f}")
    print(f"\n合計 {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
