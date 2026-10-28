"""ルール変換で作ったカードを、動作検証が通れば自動承認する（モデル不使用・無料）。承認台帳 data/cards/approvals/<弾>.json を更新する。

    python tools/auto_approve.py                 # converted.yaml / real.yaml の全カードを対象
    python tools/auto_approve.py --dry-run       # 台帳を書かず件数だけ
    python tools/auto_approve.py --limit 500     # 1回あたりの検証数の上限

手順: ① 承認済みで定義・語彙が変わったものを pending に戻す ② pending のうち「ルールのみで変換」かつ parse_card 合格のものを
verify_card（動作検証）と effectcheck（原文との突き合わせ・効果が起きるか）にかけ、全部通れば approved(by=rule)。モデル変換のカードは効果が実際に起きた（effect: ok）時だけ approved(by=check)。落ちたものは pending のまま、理由を台帳に残す。
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
from dmsim.cardfiles import card_files  # noqa: E402
from dmsim.defs import DATA, load_rules, load_tables  # noqa: E402
from dmsim import effectcheck as ec  # noqa: E402
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
    rules = load_rules(rule_files or card_files())
    todo = [cid for cid, raw in raws.items() if (ledger.get(cid) or {}).get("status") != "approved"
            and (ledger.get(cid) or {}).get("status") != "rejected"]
    for cid in todo:
        raw = raws[cid]
        is_rule = RULE_NOTE in str((raw.get("source") or {}).get("notes", ""))
        if limit is not None and stats["approved"] + stats["failed"] >= limit:
            break
        r = verify_card(rules, cid)
        checks = {}
        if r["status"] == "ok":
            for name, fn in (("text", ec.text_check), ("effect", ec.effect_check)):
                try:
                    checks[name] = fn(rules, cid)
                except Exception as e:      # 検査自体が落ちた（エンジンの未対応など）も不合格にする
                    checks[name] = {"status": "fail", "problems": [f"{type(e).__name__}: {e}"[:120]]}
        bad = [p for c in checks.values() if c["status"] == "fail" for p in c["problems"]]
        extra = {"verifier": ec.VERIFIER, "checks": {k: v["status"] for k, v in checks.items()}}
        if not is_rule and r["status"] == "ok" and not bad and checks["effect"]["status"] != "ok":
            stats["skipped_not_rule"] += 1      # モデル変換のカードは、効果が実際に起きたと確かめられた時だけ自動承認する
            continue
        if r["status"] == "ok" and not bad:
            ledger[cid] = ap.entry(raw, "approved", "rule" if is_rule else "check", versions, verify=r["detail"], **extra)
            stats["approved"] += 1
        else:
            ledger[cid] = ap.entry(raw, "pending", "rule", versions, **extra,
                                   verify_error=r["detail"] if r["status"] != "ok" else "; ".join(bad)[:300])
            stats["failed"] += 1
    if not dry_run:
        ap.save(ledger, ledger_path)
    return stats


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int)
    p.add_argument("files", nargs="*", type=Path, default=[f for f in card_files() if f.name != "proto.yaml"])
    a = p.parse_args(argv)
    print(json.dumps(run(a.files, limit=a.limit, dry_run=a.dry_run), ensure_ascii=False))


if __name__ == "__main__":
    main()
