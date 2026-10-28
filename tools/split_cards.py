"""カードのYAMLを弾（公式IDの接頭辞。dm01-001 → dm01）ごとのファイルに分ける。

    python tools/split_cards.py data/cards/converted.yaml            # → data/cards/converted/<弾>.yaml（元ファイルは残す）
    python tools/split_cards.py data/cards/converted.yaml --remove   # 分けた後に元ファイルを消す

分けたファイルは dmsim.cardfiles.card_files() が読むので、load_rules・開発者モード・承認ツールはそのまま動く。
元ファイルと分割後の両方に同じ ID があると重複エラーになるため、通常は --remove か、元を別の場所へ移す。
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import yaml

HEADER = "# {src} を弾ごとに分けたもの（tools/split_cards.py）。\n"


def split(src: Path, out_dir: Path | None = None) -> dict[str, int]:
    doc = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    groups = defaultdict(list)
    for c in doc.get("cards") or []:
        groups[c["id"].split("-")[0]].append(c)
    out_dir = out_dir or src.with_suffix("")
    out_dir.mkdir(parents=True, exist_ok=True)
    for k, cards in groups.items():
        (out_dir / f"{k}.yaml").write_text(
            HEADER.format(src=src.name) + yaml.safe_dump({"cards": sorted(cards, key=lambda c: c["id"])},
                                                         allow_unicode=True, sort_keys=False), encoding="utf-8")
    return {k: len(v) for k, v in sorted(groups.items())}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path)
    ap.add_argument("--remove", action="store_true")
    a = ap.parse_args(argv)
    stats = split(a.src)
    if a.remove:
        a.src.unlink()
    print(f"{sum(stats.values())}枚を{len(stats)}ファイルに分けた", file=sys.stderr)


if __name__ == "__main__":
    main()
