#!/usr/bin/env python3
"""拡張可能特徴量（dmsim/ai/ability_features.py）のカバレッジ測定。

全カードの能力を走査し、プリミティブごとに「その他」へ落ちる割合と、
旧属性（attributes.py、294次元）との表現力の差を表示する。

使い方: python3 tools/ability_features_coverage.py [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.ai import ability_features as AF  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None, help="JSON の出力先")
    args = ap.parse_args()

    rules = load_rules()
    schema = AF.default_schema(rules)
    rep = AF.coverage_report(rules)

    print(f"カード数: {len(rules.cards)}")
    print(f"スキーマ: block_dim={schema.block_dim} "
          f"card_dim={schema.card_dim} version={schema.version}")
    print()
    print(f"{'グループ':14s} {'出現数':>8s} {'その他':>7s} {'その他率':>8s}")
    for g, d in rep["groups"].items():
        print(f"{g:14s} {d['total']:8d} {d['other']:7d} "
              f"{d['other_rate']:8.4f}")
        for name, n in d["top_other"]:
            print(f"{'':14s}   other: {name} x{n}")
    ab = rep["abilities"]
    print()
    print(f"能力総数: {ab['total']}")
    print(f"  if を持つ能力: {ab['with_if']} "
          f"（うち turn_count 条件: {ab['with_if_turn_count']}）")
    print(f"  instead を持つ能力: {ab['with_instead']}")
    print(f"  cast_limit を持つ能力: {ab['with_cast_limit']}")
    print(f"  free_if を持つ面: {ab['with_free_if']}")
    old = rep["old_schema"]
    print()
    print("旧属性（294次元）との比較:")
    print(f"  条件の原子 {old['condition_atoms_total']} 件: "
          f"旧の被覆率 {old['condition_coverage']:.2f}（if は丸ごと欠落）")
    print(f"  mod キー出現 {old['mod_key_occurrences']} 件: "
          f"旧の専用バケット被覆率 {old['mod_key_dedicated_rate']:.3f}")
    print(f"  op 出現 {old['op_occurrences']} 件: "
          f"旧の専用枠被覆率 {old['op_dedicated_rate']:.4f}")
    print(f"  イベント出現 {old['event_occurrences']} 件: "
          f"旧の専用枠被覆率 {old['event_dedicated_rate']:.4f}")

    if args.json:
        Path(args.json).write_text(
            json.dumps(rep, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"\nJSON: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
