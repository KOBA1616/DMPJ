"""取得済みカードを OpenCode の無料モデルで定期的に変換する（.github/workflows/auto-convert.yml から呼ぶ）。

    python tools/auto_convert.py --limit 20 --interval 6 --model glm-5.3-flash-free

1. 原文（data/cards/raw）のうち未変換のカードを --limit 枚まで変換する（短い順）。
2. 語彙（スキーマ・data/rules）が前回から変わっていたら、検査落ち(rejects)を --limit 枚まで再試行する。
   変わっていなければ再試行しない（無料枠を無駄に使わないため）。
3. 進捗を data/cards/raw/convert_status.json に書く（gen_status.py が docs/STATUS.md に出す）。
無料モデルの許可リスト検査と課金検知は convert_cards.py のものがそのまま効く。違反したら Fatal で止まる。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import convert_cards as cc  # noqa: E402
from dmsim import schema  # noqa: E402
from dmsim.defs import DATA, load_tables  # noqa: E402

RAW = DATA / "cards" / "raw"
STATUS = RAW / "convert_status.json"


def vocab_hash() -> str:
    h = hashlib.sha256(json.dumps(schema.build(), sort_keys=True, ensure_ascii=False).encode())
    for n in ("zones.yaml", "keywords.yaml", "op_macros.yaml", "permissions.yaml", "turn.yaml"):
        h.update(cc._rules_text(n).encode())
    return h.hexdigest()[:16]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", default="opencode-cli", choices=["opencode", "opencode-cli"])
    ap.add_argument("--model", default=cc.OPENCODE_DEFAULT)
    ap.add_argument("--interval", type=float, default=6.0)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--effort", default="high")
    a = ap.parse_args(argv)
    out, rej = DATA / "cards" / "converted.yaml", RAW / "rejects.jsonl"
    prev = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    vh = vocab_hash()
    sysp, tables = cc.system_prompt(), load_tables()
    llm = cc.make_llm(a.provider, a.model, a.interval)
    ran = {"new": None, "retry": None}
    try:
        rows = cc.load_rows([str(RAW)])
        done = cc.known_ids(out) | ({c["id"] for c in (yaml.safe_load(out.read_text(encoding="utf-8")) or {}).get("cards") or []}
                                    if out.exists() else set())
        failed = {r["id"] for r in cc.read_jsonl(rej)}
        todo = sorted((r for r in rows if r["id"] not in done and r["id"] not in failed),
                      key=lambda r: len(r.get("text", "")))[:a.limit]
        if todo:
            ran["new"] = cc.run(todo, llm, tables, sysp, a.effort, out, rej, report_path=RAW / "convert_report.json")
        if vh != prev.get("vocab_hash") and failed:
            retry = [r for r in rows if r["id"] in failed][:a.limit]
            ran["retry"] = cc.run(retry, llm, tables, sysp, a.effort, out, rej)
        retried_all = vh == prev.get("vocab_hash") or len(failed) <= a.limit
    except cc.Fatal as e:
        print(f"停止: {e}", file=sys.stderr)
        STATUS.parent.mkdir(parents=True, exist_ok=True)
        STATUS.write_text(json.dumps({**prev, "stopped": str(e)[:300],
                                      "at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                                     ensure_ascii=False, indent=1), encoding="utf-8")
        sys.exit(1)
    converted = len({c["id"] for c in (yaml.safe_load(out.read_text(encoding="utf-8")) or {}).get("cards") or []}) if out.exists() else 0
    rejects = cc.read_jsonl(rej)
    status = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": a.model,
              "raw_total": len(rows), "converted": converted, "rejected": len(rejects),
              "pending": max(0, len(rows) - converted - len(rejects)),
              # 語彙が変わった直後で再試行しきれなかった時は、次回も再試行するよう古いハッシュを残す
              "vocab_hash": vh if retried_all else prev.get("vocab_hash"),
              "last_run": {k: (v and {x: v[x] for x in ("requested", "ok", "rejected", "api_error")}) for k, v in ran.items()}}
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
