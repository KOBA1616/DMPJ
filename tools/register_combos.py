"""combo_hunt の結果（data/combohunt/*.jsonl）から検証済みの組を拾い、計画（combo_sequence）として
data/plans/combo_sequence.jsonl に書く。plan_id で重複除去し、再実行しても同じ結果になる。
使い方: python tools/register_combos.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dmsim.plan import dump_jsonl, register_verified  # noqa: E402


def main():
    recs = []
    for f in sorted((ROOT / "data" / "combohunt").glob("*.jsonl")):
        recs += [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    plans = register_verified(recs)
    out = ROOT / "data" / "plans" / "combo_sequence.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    dump_jsonl(plans, out)
    print(f"検証済み {len(plans)} 件を {out.relative_to(ROOT)} に書いた（入力 {len(recs)} 件）")


if __name__ == "__main__":
    main()
