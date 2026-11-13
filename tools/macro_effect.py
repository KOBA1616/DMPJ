"""登録簿の手順を探索の1手にした効き目（docs/registry-design.md §9）。手あり・なしで段2を比べる。
  python tools/macro_effect.py entry   [--seeds 8] [--budget 200]   # 入口局面（ばらつきあり）
  python tools/macro_effect.py opening [--games 40] [--budget 200]  # 通常開幕（assemble.run_one、上限6ターン）"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dmsim import load_rules  # noqa: E402
from dmsim.eval import loop_entry as le  # noqa: E402
from dmsim.search import macro  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["entry", "opening"])
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--first", type=int, default=9, help="最初のシード。登録の検証（1〜8）と重ねない")
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--budget", type=int, default=200)
    ap.add_argument("--combos", default="saga,akashic")
    a = ap.parse_args(argv)
    rules = load_rules()
    for name in a.combos.split(","):
        ls = le.load(name)
        for on in (False, True):
            macro.enable(on)
            t = time.time()
            if a.mode == "entry":
                from dmsim.eval.ruler_control import run_one
                rows = [run_one(rules, ls, s, budget=a.budget) for s in range(a.first, a.first + a.seeds)]
                s2 = sum(r["stage2"] for r in rows)
                vias = [r["via"] for r in rows]
                print(f"{name} macro={on} 段2 {s2}/{len(rows)} via={vias} {time.time()-t:.0f}s", flush=True)
            else:
                from dmsim.eval.assemble import run_one
                rows = [run_one(rules, ls, s, budget=a.budget) for s in range(a.first, a.first + a.games)]
                vd = [r["verdict"] for r in rows]
                s2 = sum(v.stage2.ok for v in vd)
                kill = [v.stage2.win_turn for v in vd if v.stage2.ok]
                beat = sum(v.stage2.via == "beat" for v in vd)
                entry = sum(r["entry_turn"] is not None for r in rows)
                print(f"{name} macro={on} 段2 {s2}/{len(rows)} 勝ちターン {sorted(kill)} 殴り {beat} 入口到達 {entry} {time.time()-t:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
