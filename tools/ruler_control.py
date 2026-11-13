"""物差しの陽性対照（校正）を回す（docs/combo-ruler-design.md §12）。

  PYTHONPATH=. python tools/ruler_control.py [--seeds 8] [--per-core 4] [--stamp] [--json out.json]

既知のループ型コンボ（saga・akashic）を入口局面（シードでばらつき）から ruler.judge で測り、段2到達率を出す。
中核1種類を差し替えたランダム組も同じシードで測る。合格の印は --stamp で data/eval/ruler_control_stamp.json に書く（コミットしない）。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.eval import loop_entry as le  # noqa: E402
from dmsim.eval import ruler_control as rc  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--per-core", type=int, default=4)
    ap.add_argument("--budget", type=int, help="探索の予算を入口局面の既定から変える（参考測定用。合格の印は既定の予算でだけ書く）")
    ap.add_argument("--stamp", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    rules = load_rules()
    seeds = list(range(1, a.seeds + 1))
    t0 = time.time()
    known = {n: [rc.run_one(rules, le.load(n), sd, budget=a.budget) for sd in seeds] for n in rc.KNOWN}
    for n, rows in known.items():
        print(f"既知 {n}: 段2 {rc.rate(rows):.2f}（開始局面 {len({r['start'] for r in rows})} 種）", flush=True)
    randoms = []
    for n in rc.KNOWN:
        for g in rc.make_randoms(rules, n, a.per_core):
            g["rows"] = [rc.run_one(rules, g["spec"], sd, budget=a.budget) for sd in seeds]
            print(f"  ランダム {n} {g['old']}→{g['new']} ({rules.cards[g['new']].name}): 段2 {rc.rate(g['rows']):.2f}", flush=True)
            randoms.append(g)
    ok, why, summ = rc.judge_control(known, randoms)
    summ["seconds"] = round(time.time() - t0)
    print(f"ランダム組 中央値 {summ['random_median']:.3f} 最大 {summ['random_max']:.2f}（{len(randoms)} 組）")
    print("物差しの陽性対照:", "合格" if ok else "不合格 — " + why)
    if a.stamp and a.budget is None:
        rc.write_stamp(ok, why, summ)
    if a.json:
        out = {"passed": ok, "reason": why, "summary": summ,
               "known_rows": known, "random_rows": [{k: v for k, v in g.items() if k != "spec"} for g in randoms]}
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
