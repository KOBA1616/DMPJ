"""監査（dmsim/dataaudit.py）が text_but_no_effect などで挙げたカードを、原文からルール変換し直して converted.yaml の該当カードを差し替える。

    PYTHONPATH=. python tools/reconvert_flagged.py [--code text_but_no_effect] [--dry-run]

ルールで変換できて検査（parse_card）を通ったものだけ差し替える。通らないものは触らず一覧に出す（モデル・人の対応へ）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import convert_cards as cc  # noqa: E402
import rule_convert  # noqa: E402
from dmsim import cardstore  # noqa: E402
from dmsim.dataaudit import audit_rules  # noqa: E402
from dmsim.defs import DATA, DefError, load_rules, load_tables  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default="text_but_no_effect")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    flagged = set(audit_rules(load_rules()).get(a.code, []))
    out = cardstore.converted_path(DATA)
    cards = cardstore.read(out)
    rows = {r["id"]: r for r in cc.load_rows([str(DATA / "cards" / "raw")])}
    tables = load_tables()
    fixed, left = [], []
    for i, c in enumerate(cards):
        cid = c["id"]
        if cid not in flagged:
            continue
        row = rows.get(cid)
        rc = rule_convert.convert(row) if row else None
        if rc is not None:
            try:
                rc = cc.validate(rc, row, tables)
            except DefError as e:
                print(f"  {cid}: 検査落ち {e}", file=sys.stderr)
                rc = None
        if rc is None:
            left.append(cid)
            continue
        old_src = c.get("source") or {}
        rc["source"] = {**rc.get("source", {}), **{k: v for k, v in old_src.items() if k in ("aliases",)}}
        cards[i] = rc
        fixed.append(cid)
    if fixed and not a.dry_run:
        cardstore.write(out, cards, cc.CONVERTED_HEADER)
    print(f"差し替え {len(fixed)} 枚: {fixed}\nルールで直せない {len(left)} 枚: {left}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
