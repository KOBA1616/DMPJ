"""ゴールデンケースの回帰ランナー。

探索ツールを改修した後に、既知の判定（勝ち／勝ちなし証明／キルターン）が
変わっていないかを1コマンドで確認する。ケース定義は tools/golden_cases.yaml。

使い方:
  python tools/run_golden.py                 # 全ケース実行
  python tools/run_golden.py proto-b-nokill-proof ...   # ケースIDで絞る

各ケースを subprocess で実行し（cwd=リポジトリルート）、出力 JSONL ログの
case_result を期待値と照合する。ケースごとに PASS/FAIL を出し、FAIL が
1件でもあれば終了コード 1。

verdict の正規化: ツールごとに kill の記録形式が違う
（exhaustive_multiturn は "kill_3_4" のようにキルターンを埋め込む）ため、
"kill" または "kill_" で始まる verdict は全て "kill" に寄せてから照合する。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CASES_FILE = Path(__file__).resolve().parent / "golden_cases.yaml"


def canonical_verdict(v) -> str | None:
    if v is None:
        return None
    if v == "kill" or v.startswith("kill_"):
        return "kill"
    return v


def find_case_result(log_path: Path, match: dict) -> dict | None:
    """ログから match 条件（case 完全一致、mode は指定時）に合う最後の case_result を返す。"""
    if not log_path.exists():
        return None
    found = None
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("kind") != "case_result":
            continue
        if obj.get("case") != match.get("case"):
            continue
        if match.get("mode") is not None and obj.get("mode") != match["mode"]:
            continue
        found = obj
    return found


def run_case(case: dict) -> tuple[bool, str, float]:
    """1ケース実行して (合否, 詳細メッセージ, 所要秒) を返す。"""
    argv = [sys.executable] + [str(x) for x in case["argv"]]
    timeout = case.get("timeout", 300)
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"timeout ({timeout}s)", time.perf_counter() - t0
    dt = time.perf_counter() - t0
    if proc.returncode != 0:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-5:]
        return False, f"exit code {proc.returncode}: " + " / ".join(tail), dt

    res = find_case_result(ROOT / case["out"], case["match"])
    if res is None:
        return False, f"case_result not found in {case['out']} (match={case['match']})", dt

    expect = case["expect"]
    got_v = canonical_verdict(res.get("verdict"))
    if got_v != expect["verdict"]:
        return False, f"verdict: expected {expect['verdict']}, got {res.get('verdict')}", dt
    if "kill_turn" in expect and res.get("kill_turn") != expect["kill_turn"]:
        return False, (f"kill_turn: expected {expect['kill_turn']}, "
                       f"got {res.get('kill_turn')} (verdict {res.get('verdict')})"), dt
    detail = f"verdict={res.get('verdict')}"
    if res.get("kill_turn") is not None:
        detail += f" kill_turn={res['kill_turn']}"
    if res.get("nodes") is not None:
        detail += f" nodes={res['nodes']}"
    return True, detail, dt


def main():
    ap = argparse.ArgumentParser(description="ゴールデンケース回帰ランナー")
    ap.add_argument("ids", nargs="*", help="実行するケースID（省略時は全ケース）")
    a = ap.parse_args()

    doc = yaml.safe_load(CASES_FILE.read_text(encoding="utf-8"))
    cases = doc["cases"]
    if a.ids:
        want = set(a.ids)
        cases = [c for c in cases if c["id"] in want]
        missing = want - {c["id"] for c in cases}
        if missing:
            print(f"unknown case id: {sorted(missing)}", flush=True)
            return 1

    print(f"golden cases: {len(cases)}", flush=True)
    t_all = time.perf_counter()
    fails = 0
    for case in cases:
        ok, detail, dt = run_case(case)
        fails += 0 if ok else 1
        print(f"[{'PASS' if ok else 'FAIL'}] {case['id']} ({dt:.1f}s) {detail}", flush=True)
    total = time.perf_counter() - t_all
    print(f"== {len(cases) - fails}/{len(cases)} passed, total {total:.1f}s", flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
