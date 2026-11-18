"""シード並列ランナー: 同じコマンドをシードごとに独立プロセスで並列実行する。

ケース（シード）同士は状態を持たないため、プロセスを分ければそのまま
並列化できる。各ワーカーは resume_driver に委譲するので、分割実行の
再開もそのまま効く。母集団スキャン（複数シードの一括実行）の実行形。

使い方:
  python3 tools/run_parallel.py --jobs 2 --seeds 1,2 \
      --stop-kinds case_result --out-pattern logs/par_{seed}.jsonl \
      -- python3 tools/exhaustive_crossturn.py --setup ... \
         --seeds {seed} --out {out} --store-dir logs/par_{seed}

プレースホルダ: コマンドとパターンの中の {seed} と {out} を置換する。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRIVER = ROOT / "tools" / "resume_driver.py"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--seeds", required=True, help="カンマ区切り")
    ap.add_argument("--stop-kinds", required=True)
    ap.add_argument("--out-pattern", required=True,
                    help="シードごとの JSONL 出力（{seed} を含む）")
    ap.add_argument("--resume-when-pattern", default=None,
                    help="resume_driver の --resume-when（{seed} 可）")
    ap.add_argument("--max-iters", type=int, default=500)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    if not cmd:
        ap.error("コマンドが空です（-- の後に指定してください）")
    seeds = [s.strip() for s in a.seeds.split(",") if s.strip()]

    def build(seed: str):
        out = a.out_pattern.replace("{seed}", seed)
        c = [x.replace("{seed}", seed).replace("{out}", out) for x in cmd]
        d = [sys.executable, str(DRIVER), "--sentinel", out,
             "--stop-kinds", a.stop_kinds, "--max-iters", str(a.max_iters)]
        if a.resume_when_pattern:
            d += ["--resume-when",
                  a.resume_when_pattern.replace("{seed}", seed)]
        return d + ["--"] + c

    running: dict[str, subprocess.Popen] = {}
    results: dict[str, int] = {}
    queue = list(seeds)
    while queue or running:
        while queue and len(running) < a.jobs:
            s = queue.pop(0)
            print(f"[parallel] start seed {s}", flush=True)
            running[s] = subprocess.Popen(build(s), cwd=ROOT)
        time.sleep(2)
        for s in list(running):
            rc = running[s].poll()
            if rc is not None:
                results[s] = rc
                print(f"[parallel] seed {s}: rc={rc}", flush=True)
                del running[s]
    bad = {s: rc for s, rc in results.items() if rc != 0}
    print(f"[parallel] done: {len(results) - len(bad)}/{len(results)} ok",
          flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
