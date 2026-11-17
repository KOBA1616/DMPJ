"""鎖ゲート: 段階目標の鎖の採否を判定する定型測定（docs/phase-chain-plan.md §5）。

候補の鎖について2つの測定を行い、基準と照らして PASS/FAIL を出す:
1. 診断（plan_leaf_diag）: hidden seed1 のターン1終了局面で、最速キル局面の
   充足率順位が beam 幅（4）以内に入るか。
2. 保持テスト（exhaustive_crossturn beam4 + trim-order plan）: hidden seed1〜4 と
   prep seed1〜3 で最速キル（2ターン）を保持できるか。ノード数は順序関数 v2 の
   実測（基準値）を大きく超えないか。

使い方:
  python tools/chain_gate.py --stages-file tools/saga_extracted_stages.yaml
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 順序関数 v2（trim-order ruler）の beam4 実測ノード数（報告書 §5.7）
BASELINE_NODES = {("saga_hidden_setup", 1): 5003, ("saga_hidden_setup", 2): 5025,
                  ("saga_hidden_setup", 3): 5025, ("saga_hidden_setup", 4): 5003,
                  ("saga_prep_setup", 1): 4655, ("saga_prep_setup", 2): 4607,
                  ("saga_prep_setup", 3): 4767}
NODE_TOLERANCE = 1.5


def run(cmd: list[str], timeout: int) -> str:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return p.stdout + p.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages-file", required=True)
    ap.add_argument("--skip-diag", action="store_true")
    a = ap.parse_args()
    py = sys.executable
    ok = True

    if not a.skip_diag:
        print("[gate] diag: plan_leaf_diag hidden seed1 ...", flush=True)
        out = run([py, "tools/plan_leaf_diag.py", "--setup", "tests/saga_hidden_setup.yaml",
                   "--seed", "1", "--stages-file", a.stages_file], timeout=1200)
        m = re.search(r"fastest kill turn=(\d+): frac-rank \[([0-9, ]+)\]", out)
        if not m:
            print("[gate] diag: FAIL (fastest-kill line not found)", flush=True)
            ok = False
        else:
            ranks = [int(x) for x in m.group(2).split(",")]
            passed = min(ranks) <= 3
            ok = ok and passed
            print(f"[gate] diag: fastest kill turn={m.group(1)} frac-ranks={ranks} "
                  f"-> {'PASS' if passed else 'FAIL'}", flush=True)

    for setup, seeds in [("tests/saga_hidden_setup.yaml", "1,2,3,4"),
                         ("tests/saga_prep_setup.yaml", "1,2,3")]:
        name = Path(setup).stem
        print(f"[gate] beam4 plan: {name} seeds {seeds} ...", flush=True)
        out = run([py, "tools/exhaustive_crossturn.py", "--setup", setup, "--seeds", seeds,
                   "--mode", "beam", "--beam", "4", "--trim-order", "plan",
                   "--stages-file", a.stages_file,
                   "--out", f"logs/gate_{name}.jsonl"], timeout=1800)
        for line in out.splitlines():
            m = re.search(r"seed(\d+) .* (KILL|NO-KILL|UNKNOWN|ERROR) kill_turn=(\d+|None) nodes=(\d+)", line)
            if not m:
                continue
            seed, verdict, kt, nodes = int(m.group(1)), m.group(2), m.group(3), int(m.group(4))
            base = BASELINE_NODES.get((name, seed))
            kt_ok = verdict == "KILL" and kt == "2"
            nodes_ok = base is None or nodes <= base * NODE_TOLERANCE
            passed = kt_ok and nodes_ok
            ok = ok and passed
            print(f"[gate]   {name} seed{seed}: {verdict} kill_turn={kt} nodes={nodes} "
                  f"(baseline {base}) -> {'PASS' if passed else 'FAIL'}", flush=True)

    print(f"[gate] RESULT: {'PASS' if ok else 'FAIL'} ({a.stages_file})", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
