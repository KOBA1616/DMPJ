"""対象カード（サイキック・GR を除く）の変換・検査・承認の割合と、承認に進めない理由の内訳を数える（読むだけ。何も書かない）。

    git fetch origin cards-data
    python tools/approval_stats.py                          # 台帳は data/cards/approvals（無ければ origin/cards-data から読む）
    python tools/approval_stats.py --ledger DIR --json      # 台帳の場所を指定、JSON で出す

承認の判定は load_rules(only_approved=True) と同じ approval.is_usable を使う（今のコードの語彙で古くなった承認は数えない）。
"""
from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dmsim.cards import approval as ap  # noqa: E402
from dmsim.cards.cardfiles import card_files  # noqa: E402
from dmsim.cards.defs import load_tables, parse_card  # noqa: E402
from dmsim.cards.canonical import name_key  # noqa: E402

RAW = ROOT / "data" / "cards" / "raw"
EXCLUDE = ("サイキック", "GR")


def excluded(card_type: str) -> bool:
    return any(k in (card_type or "") for k in EXCLUDE)


def targets() -> dict[str, dict]:
    out = {}
    for f in sorted((RAW / "by_product").glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["id"]] = r
    return out


def ledger_from_branch(ref: str = "origin/cards-data") -> dict:
    try:
        names = subprocess.run(["git", "ls-tree", "--name-only", f"{ref}:data/cards/approvals/"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.split()
    except subprocess.CalledProcessError:
        return {}
    led = {}
    for n in names:
        if n.endswith(".json"):
            led.update(json.loads(subprocess.run(["git", "show", f"{ref}:data/cards/approvals/{n}"], cwd=ROOT,
                                                 capture_output=True, text=True, check=True).stdout))
    return led


def reject_kind(r: dict) -> str:
    e = str(r.get("error") or r.get("reason") or "")
    if r.get("gaps") or "語彙" in e or "未対応" in e:
        return "変換失敗: 未対応の効果（語彙不足）"
    if "能力文が無い" in e:
        return "変換失敗: 能力文が無い"
    if "秒以内" in e or "Timeout" in e:
        return "変換失敗: 時間切れ"
    if "検査" in e:
        return "変換失敗: 出力が検査を通らない"
    return "変換失敗: その他"


def run(ledger: dict) -> dict:
    tables = load_tables()
    versions = ap.vocab_versions(tables)
    tg = {k: v for k, v in targets().items() if not excluded(v.get("card_type"))}
    raws = {}
    for f in card_files():
        for c in (yaml.safe_load(Path(f).read_text(encoding="utf-8")) or {}).get("cards") or []:
            raws[c["id"]] = c
    rejects = {}
    rj = RAW / "rejects.jsonl"
    if rj.exists():
        for line in rj.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                rejects[r["id"]] = r
    st = collections.Counter()
    why = collections.Counter()
    gaps = collections.Counter()
    for cid in tg:
        raw = raws.get(cid)
        if raw is None:
            if cid in rejects:
                why[reject_kind(rejects[cid])] += 1
                for g in rejects[cid].get("gaps") or []:
                    gaps[str(g)[:40]] += 1
            else:
                why["未変換（変換待ち）"] += 1
            continue
        st["converted"] += 1
        try:
            parse_card(raw, tables)
        except Exception:
            why["変換済み: 定義の検査(parse_card)落ち"] += 1
            continue
        st["parsed"] += 1
        e = ledger.get(cid)
        if ap.is_usable(raw, ledger, versions):
            st["approved"] += 1
            st["approved_by_" + ((e or {}).get("by") if e and e.get("status") == "approved" else "file")] += 1
            continue
        if not e:
            why["検査通過: 自動承認にまだ掛けていない（台帳に無い）"] += 1
        elif e.get("status") == "approved":
            why["承認済みだが古い: " + (ap.stale_reason(e, raw, versions) or "?")] += 1
        elif e.get("status") == "rejected":
            why["人が却下"] += 1
        else:
            why["動作検査・原文照合で不合格（台帳 pending）"] += 1
    n = len(tg)
    return {"targets": n, "targets_unique_names": len({name_key(v.get("name") or "") for v in tg.values()}),
            "ledger_entries": len(ledger), **st,
            "rate": {k: round(st[k] / n, 4) for k in ("converted", "parsed", "approved")},
            "blocked": dict(why.most_common()), "top_gaps": dict(gaps.most_common(15))}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--ledger", type=Path, default=None)
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    if a.ledger:
        led = ap.load(a.ledger)
    elif ap.LEDGER.exists():
        led = ap.load(ap.LEDGER)
    else:
        led = ledger_from_branch()
    out = run(led)
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    n = out["targets"]
    print(f"対象 {n} 枚（サイキック・GR 除く、名前の異なり {out['targets_unique_names']}）、台帳 {out['ledger_entries']} 件")
    for k, label in (("converted", "変換済み"), ("parsed", "定義の検査通過"), ("approved", "承認済み(有効)")):
        print(f"  {label}: {out.get(k, 0)} ({out['rate'][k]:.1%})")
    for k, v in out.items():
        if k.startswith("approved_by_"):
            print(f"    うち {k[12:]}: {v}")
    print("承認に進めない理由:")
    for k, v in out["blocked"].items():
        print(f"  {v:6d}  {k}")


if __name__ == "__main__":
    main()
