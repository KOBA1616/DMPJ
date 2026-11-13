"""変換モデルの精度測定: 手作業で確認済みの実カードを原文から変換し直し、正解（data/cards/real*.yaml）との一致率を出す。

    OPENCODE_API_KEY=... python tools/eval_convert.py data/cards/raw --provider opencode --limit 20

- 答えが例に載らないよう、測るカードは system prompt の例から外す。
- 一致 = 構造（keywords・types・civs・cost・power・effects 等）が完全一致。キーごとの一致率も出す。
- 結果は data/cards/raw/eval_report.json。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import convert_cards as cc  # noqa: E402
from dmsim.cards.defs import DATA, load_tables  # noqa: E402

SKIP = {"source", "text"}


def gold_cards() -> dict[str, dict]:
    out = {}
    for f in sorted((DATA / "cards").glob("real*.yaml")):
        for c in (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("cards") or []:
            out[c["id"]] = c
    return out


def compare(pred: dict, gold: dict) -> dict[str, bool]:
    keys = (set(pred) | set(gold)) - SKIP
    return {k: pred.get(k) == gold.get(k) for k in sorted(keys)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw", nargs="+")
    ap.add_argument("--provider", choices=["anthropic", "opencode", "opencode-cli"], default="opencode")
    ap.add_argument("--model")
    ap.add_argument("--interval", type=float, default=3.0)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--effort", default="high")
    ap.add_argument("--report", default=str(DATA / "cards" / "raw" / "eval_report.json"))
    a = ap.parse_args(argv)
    gold = gold_cards()
    rows = [r for r in cc.load_rows(a.raw) if r["id"] in gold][:a.limit]
    sysp = cc.system_prompt(frozenset(r["id"] for r in rows))
    tables, per_card = load_tables(), {}
    try:
        llm = cc.make_llm(a.provider, a.model, a.interval)
        for r in rows:
            try:
                pred = cc.convert(llm, r, tables, sysp, a.effort)
                per_card[r["id"]] = compare(pred, gold[r["id"]])
            except cc.DefError as e:
                per_card[r["id"]] = {"_rejected": False, "error": str(e)[:200]}
    except cc.Fatal as e:
        sys.exit(f"停止: {e}")
    exact = [i for i, d in per_card.items() if d and all(v is True for k, v in d.items() if k != "error")]
    keyacc: dict[str, list] = {}
    for d in per_card.values():
        for k, v in d.items():
            if k not in ("error", "_rejected"):
                keyacc.setdefault(k, []).append(v)
    rep = {"n": len(per_card), "exact": len(exact), "exact_rate": len(exact) / max(1, len(per_card)),
           "rejected": sum(1 for d in per_card.values() if "_rejected" in d),
           "by_key": {k: sum(v) / len(v) for k, v in keyacc.items()}, "cards": per_card}
    Path(a.report).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"完全一致 {rep['exact']}/{rep['n']}（検査落ち {rep['rejected']}）。キー別: "
          + ", ".join(f"{k}={v:.0%}" for k, v in rep["by_key"].items()), file=sys.stderr)


if __name__ == "__main__":
    main()
