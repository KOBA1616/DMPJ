"""実験ログ（JSONL）の集計表を出す道具。

全探索系の各ツール（exhaustive_multiturn / exhaustive_crossturn /
exhaustive_proto）が出す構造化 JSONL ログを読み、ファイル×ケース接頭辞
（case 名から seed 部分を除いたもの）ごとに、件数・キル数・キルターンの
内訳・no-kill 証明数・unknown 数・エラー数・キル率（Wilson 95% 信頼区間）
を表にする。今まで手作業スクリプトで集計していたものの定型化
（docs/search-and-foundation-plan.md フェーズ3）。

判定の正規化: verdict が "kill" で始まるもの（kill、kill_3_4 等）はキル、
"no-kill" は証明、"error" はエラー、その他（unknown / lost 等）はそのまま数える。

使い方:
  python tools/scan_report.py logs/scan2_*.jsonl logs/scan3_*.jsonl
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

SEED_RE = re.compile(r"\s*seed\d+")
SETTING_KEYS = ("mode", "order", "stages", "stage", "trim_order", "stages_file",
                "beam", "budget_per_turn", "budget", "max_turn")


def case_prefix(case: str) -> str:
    """case 名から seed 部分を除いた接頭辞（例: 'saga seed1 T4' -> 'saga T4'）。"""
    return SEED_RE.sub("", case).strip()


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """キル率の Wilson スコア信頼区間（標準ライブラリのみ）。"""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, center - half), min(1.0, center + half))


def load_log(path: Path) -> tuple[dict, list[dict]]:
    header: dict = {}
    results: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("kind") == "header":
            header = r
        elif r.get("kind") == "case_result":
            results.append(r)
    return header, results


def settings_summary(header: dict) -> str:
    s = header.get("settings") or {}
    parts = [f"{k}={s[k]}" for k in SETTING_KEYS if k in s and s[k] is not None]
    return ", ".join(parts)


def aggregate(results: list[dict]) -> dict:
    kills = [r for r in results if str(r.get("verdict", "")).startswith("kill")]
    return {
        "n": len(results),
        "kill": len(kills),
        "kill_turns": Counter(r.get("kill_turn") for r in kills),
        "proof": sum(1 for r in results if r.get("verdict") == "no-kill"),
        "unknown": sum(1 for r in results if r.get("verdict") == "unknown"),
        "error": sum(1 for r in results if r.get("verdict") == "error"),
        "other": Counter(str(r.get("verdict")) for r in results
                         if not str(r.get("verdict", "")).startswith("kill")
                         and r.get("verdict") not in ("no-kill", "unknown", "error")),
    }


def fmt_row(label: str, agg: dict) -> str:
    turns = ", ".join(f"{t}T×{c}" for t, c in sorted(
        agg["kill_turns"].items(), key=lambda kv: (kv[0] is None, kv[0])))
    lo, hi = wilson(agg["kill"], agg["n"])
    rate = f"{agg['kill'] / agg['n']:.0%} [{lo:.0%}-{hi:.0%}]" if agg["n"] else "-"
    other = ""
    if agg["other"]:
        other = " その他:" + ",".join(f"{k}×{v}" for k, v in sorted(agg["other"].items()))
    return (f"{label:<44} {agg['n']:>4}件 キル{agg['kill']:>3} ({turns or '-'}) "
            f"証明{agg['proof']:>3} unknown{agg['unknown']:>4} error{agg['error']:>2} "
            f"キル率 {rate}{other}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+", help="JSONL ログファイル（glob 可）")
    a = ap.parse_args()

    files: list[Path] = []
    for pat in a.logs:
        matched = sorted(glob.glob(pat))
        if not matched:
            print(f"warn: no files matched: {pat}", file=sys.stderr)
        files.extend(Path(m) for m in matched)
    files = sorted(set(files))
    if not files:
        print("no log files", file=sys.stderr)
        return 1

    grand: list[dict] = []
    for path in files:
        header, results = load_log(path)
        tool = header.get("tool", "?")
        summ = settings_summary(header)
        print(f"== {path.name} [{tool}]" + (f" ({summ})" if summ else ""))
        groups: dict[str, list[dict]] = {}
        for r in results:
            groups.setdefault(case_prefix(str(r.get("case", ""))), []).append(r)
        for prefix in sorted(groups):
            print("  " + fmt_row(prefix, aggregate(groups[prefix])))
        if len(groups) > 1:
            print("  " + fmt_row("（ファイル合計）", aggregate(results)))
        grand.extend(results)
        print()
    print("== 全ファイル合計")
    print("  " + fmt_row("total", aggregate(grand)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
