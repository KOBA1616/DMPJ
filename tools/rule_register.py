"""ルールだけで完全に変換できるカードを、モデルを使わずに data/cards/converted.yaml へ登録する。

    python tools/rule_register.py            # 原文（data/cards/raw）のうち未登録のもの全部
    python tools/rule_register.py --dry-run  # 登録せず枚数だけ

キーワードのみ・バニラ・定型の効果文・定型の呪文・同一原文の写しが対象。検査（parse_card）を通ったものだけ登録し、
通らないものは触らない（モデルのジョブに回る）。auto_convert.py も開始時に同じ処理を行う。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import convert_cards as cc  # noqa: E402
from dmsim.defs import DATA, load_tables  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    raw = DATA / "cards" / "raw"
    out, rej = DATA / "cards" / "converted.yaml", raw / "rejects.jsonl"
    rows = cc.load_rows([str(raw)])
    if a.dry_run:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            stats = cc.run_rules(rows, load_tables(), Path(d) / "c.yaml", Path(d) / "r.jsonl")
    else:
        stats = cc.run_rules(rows, load_tables(), out, rej)
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
