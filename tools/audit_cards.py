"""カードデータ監査。新しい違反があれば終了コード1。

  PYTHONPATH=. python tools/audit_cards.py                    # 基準線との差分を検査
  PYTHONPATH=. python tools/audit_cards.py --summary          # 違反コードごとの件数
  PYTHONPATH=. python tools/audit_cards.py --update-baseline  # 基準線を更新（解消した分を外す。増やす更新は理由を PR に書く）
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.cards.dataaudit import audit_rules, new_violations  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402

BASELINE = Path(__file__).resolve().parent.parent / "data" / "audit" / "baseline.json"


def load_baseline() -> dict:
    try:
        return json.loads(BASELINE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--update-baseline", action="store_true")
    a = ap.parse_args(argv)
    found = audit_rules(load_rules())
    if a.update_baseline:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(found, ensure_ascii=False, indent=0), encoding="utf-8")
        print("基準線を更新:", {k: len(v) for k, v in found.items()})
        return 0
    if a.summary:
        for k, v in found.items():
            print(f"{len(v):5d} {k}  例: {v[:3]}")
    new = new_violations(found, load_baseline())
    for k, v in new.items():
        print(f"NG 新しい違反 {k}: {v[:10]}{' …' if len(v) > 10 else ''}")
    if not new:
        print("OK（新しい違反なし）")
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
