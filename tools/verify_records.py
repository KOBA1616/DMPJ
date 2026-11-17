"""記録（make_record 形式）の再生検証をまとめて行う道具。

キル記録が貯まるたびに使い捨てスクリプトで digest 照合をしていた手作業の
定型化（docs/search-and-foundation-plan.md フェーズ3 の自動化候補1）。
各記録を replay_record(strict=True) で再生し、最終状態の digest と
カード定義のハッシュが記録時と一致するかを確認する。

使い方:
  python tools/verify_records.py --records 'logs/exhaustive_records/*.json'
  python tools/verify_records.py --records 'logs/exhaustive_records/crossturn_*.json' \
      'logs/exhaustive_records/saga_*.json'

終了コード: FAIL が1件でもあれば 1、全件 OK なら 0。
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dmsim import load_rules  # noqa: E402
from dmsim.engine.play import replay_record  # noqa: E402


def summarize_result(result) -> str:
    """再生結果 {winner, reason, turn} の表示用文字列。"""
    if result is None:
        return "result=None"
    return "result={winner: %s, reason: %s, turn: %s}" % (
        result.get("winner"), result.get("reason"), result.get("turn"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", nargs="+", required=True,
                    help="記録ファイルの glob（複数指定可）")
    a = ap.parse_args()

    files = sorted({f for pat in a.records for f in glob.glob(pat)})
    if not files:
        print("対象ファイルがありません", file=sys.stderr)
        return 1

    rules = load_rules()
    print(f"rules loaded, {len(files)} records", flush=True)

    ok = 0
    for f in files:
        name = Path(f).name
        try:
            rec = json.loads(Path(f).read_text(encoding="utf-8"))
            eng = replay_record(rules, rec, strict=True)
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"
            if len(msg) > 160:
                msg = msg[:157] + "..."
            print(f"FAIL {name} {msg}", flush=True)
            continue
        ok += 1
        print(f"OK {name} {summarize_result(eng.s.result)}", flush=True)

    print(f"{ok}/{len(files)} OK", flush=True)
    return 0 if ok == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(main())
