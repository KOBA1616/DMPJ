"""再開ループドライバ（汎用）: 分割実行に対応したツール（chain_label /
exhaustive_crossturn --store-dir）を、完了レコードが出るまで --resume
付きで回し続ける。環境の再起動でプロセスが落ちても、このドライバを
再投入すれば目録から続く。

使い方:
  python3 tools/resume_driver.py \
      --sentinel logs/chain_label_x.jsonl --stop-kinds label_result \
      --resume-when logs/chain_label_x \
      -- python3 tools/chain_label.py --deck ... --store-dir logs/chain_label_x \
         --out logs/chain_label_x.jsonl --chunk-nodes 100000

- --resume は2回目以降は常に付ける。1回目でも --resume-when のパスが
  どれか存在すれば付ける（再起動後の再投入で新規開始に化けないため）。
- 終了条件: sentinel（JSONL）に --stop-kinds の kind を持つレコードが
  現れる、コマンドが2回連続で非ゼロ終了する、--max-iters に達する。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def finished(sentinel: Path, kinds: set[str]) -> str | None:
    if not sentinel.exists():
        return None
    found = None
    for line in sentinel.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("kind") in kinds:
            found = r["kind"]
    return found


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sentinel", required=True,
                    help="完了判定に使う JSONL のパス（リポジトリ相対）")
    ap.add_argument("--stop-kinds", required=True,
                    help="完了とみなす kind（カンマ区切り）")
    ap.add_argument("--resume-when", action="append", default=[],
                    help="このパスが存在すれば1回目から --resume を付ける")
    ap.add_argument("--max-iters", type=int, default=500)
    ap.add_argument("--timeout", type=int, default=3600,
                    help="1回の実行の上限秒")
    ap.add_argument("cmd", nargs=argparse.REMAINDER,
                    help="-- の後にツールのコマンド（--resume なしで）")
    a = ap.parse_args(argv)
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    if not cmd:
        ap.error("コマンドが空です（-- の後に指定してください）")
    sentinel = ROOT / a.sentinel
    kinds = {k.strip() for k in a.stop_kinds.split(",") if k.strip()}
    fails = 0
    for i in range(a.max_iters):
        done = finished(sentinel, kinds)
        if done:
            print(f"[driver] finished: {done}", flush=True)
            return 0
        run = list(cmd)
        resume = i > 0 or any((ROOT / p).exists() for p in a.resume_when) \
            or sentinel.exists()
        if resume and "--resume" not in run:
            run.append("--resume")
        t0 = time.time()
        p = subprocess.run(run, cwd=ROOT, timeout=a.timeout)
        print(f"[driver] iter {i}: rc={p.returncode} "
              f"wall={time.time() - t0:.0f}s", flush=True)
        if p.returncode != 0:
            fails += 1
            if fails >= 2:
                print("[driver] 2回連続で失敗したため停止", flush=True)
                return 1
        else:
            fails = 0
    print("[driver] iteration limit", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
