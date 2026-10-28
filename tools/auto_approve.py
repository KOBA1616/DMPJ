"""ルール変換で作ったカードを、動作検証が通れば自動承認する（モデル不使用・無料）。承認台帳 data/cards/approvals.json を更新する。

    python tools/auto_approve.py                 # converted.yaml / real.yaml の全カードを対象
    python tools/auto_approve.py --dry-run       # 台帳を書かず件数だけ
    python tools/auto_approve.py --limit 500     # 1回あたりの検証数の上限

手順: ① 承認済みで定義・語彙が変わったものを pending に戻す ② pending のうち「ルールのみで変換」かつ parse_card 合格のものを
verify_card（動作検証）にかけ、ok なら approved(by=rule)。落ちたものは pending のまま、理由を台帳に残す。
人が開発者モードで付けた承認（by=human）は、定義・語彙が変わらない限り触らない。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim import approval as ap  # noqa: E402
from dmsim.defs import DATA, load_rules, load_tables  # noqa: E402
from dmsim.verify import verify_card  # noqa: E402

RULE_NOTE = "ルールのみで変換"


def read_raws(files) -> dict[str, dict]:
    raws = {}
    for f in files:
        for c in (yaml.safe_load(Path(f).read_text(encoding="utf-8")) or {}).get("cards") or []:
            raws[c["id"]] = c
    return raws


def run(files, ledger_path=ap.LEDGER, limit=None, dry_run=False, rule_files=None) -> dict:
    raws = read_raws(files)
    versions = ap.vocab_versions(load_tables())
    ledger = ap.load(ledger_path)
    stats = {"cards": len(raws), "invalidated": len(ap.invalidate(ledger, raws, versions)),
             "approved": 0, "failed": 0, "skipped_not_rule": 0}
    rules = load_rules(rule_files or sorted((DATA / "cards").glob("*.yaml")))
    todo = [cid for cid, raw in raws.items() if (ledger.get(cid) or {}).get("status") != "approved"
            and (ledger.get(cid) or {}).get("status") != "rejected"]
    for cid in todo:
        raw = raws[cid]
        if RULE_NOTE not in str((raw.get("source") or {}).get("notes", "")):
            stats["skipped_not_rule"] += 1
            continue
        if limit is not None and stats["approved"] + stats["failed"] >= limit:
            break
        r = verify_card(rules, cid)
        if r["status"] == "ok":
            ledger[cid] = ap.entry(raw, "approved", "rule", versions, verify=r["detail"])
            stats["approved"] += 1
        else:
            ledger[cid] = ap.entry(raw, "pending", "rule", versions, verify_error=r["detail"])
            stats["failed"] += 1
    if not dry_run:
        ap.save(ledger, ledger_path)
    return stats


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int)
    p.add_argument("files", nargs="*", type=Path, default=[DATA / "cards" / "converted.yaml", DATA / "cards" / "real.yaml"])
    a = p.parse_args(argv)
    print(json.dumps(run(a.files, limit=a.limit, dry_run=a.dry_run), ensure_ascii=False))


if __name__ == "__main__":
    main()
