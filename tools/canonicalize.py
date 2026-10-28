"""変換済みカードの同一性を整える（同名は最新版のIDと本文を採用）。承認台帳も合わせて更新する。モデル不使用。

    python tools/canonicalize.py            # converted（ファイル/弾別ディレクトリ）と承認台帳を更新
    python tools/canonicalize.py --dry-run  # 件数だけ

旧IDのカードは、本文が最新版と同じなら最新IDに付け替えて承認を引き継ぎ（by=inherit）、違えば消して承認を取り消す
（最新版の原文は次の変換で変換され、承認も再検証される）。弾別ディレクトリなら、付け替えで弾が変わるカードも移る。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim import approval as ap  # noqa: E402
from dmsim import cardstore, identity  # noqa: E402
from dmsim.defs import DATA, load_tables  # noqa: E402

HEADER = "# convert_cards.py の出力（review: pending）。確認後に real.yaml へ移す。\n"


def run(conv: Path, ledger_path: Path = ap.LEDGER, dry_run: bool = False) -> dict:
    cards = cardstore.read(conv)
    ledger = ap.load(ledger_path)
    stats = identity.relocate(cards, ledger, ap.vocab_versions(load_tables()))
    if not dry_run and any(stats.values()):
        cardstore.write(conv, cards, HEADER)
        ap.save(ledger, ledger_path)
    return stats


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--converted", type=Path, default=cardstore.converted_path(DATA))
    a = p.parse_args(argv)
    print(json.dumps(run(a.converted, dry_run=a.dry_run), ensure_ascii=False))


if __name__ == "__main__":
    main()
