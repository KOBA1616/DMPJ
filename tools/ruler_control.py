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
    ap.add_argument("--opp-level", type=int, default=0, help="相手の抵抗の段階（0 既定、1 は盾に S・トリガー）")
    ap.add_argument("--max-turn", type=int, default=2)
    ap.add_argument("--known", help="測る入口局面（カンマ区切り。既定は ruler_control.KNOWN）")
    ap.add_argument("--workers", type=int, default=None, help="局ごとのプロセス並列（既定 DMSIM_WORKERS、1 は逐次。結果は逐次と同じ）")
    ap.add_argument("--stamp", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    rules = load_rules()
    if a.known:
        rc.KNOWN = tuple(a.known.split(","))
    seeds = list(range(1, a.seeds + 1))
    t0 = time.time()
    from dmsim.eval.parallel import map_ordered
    groups = [g for n in rc.KNOWN for g in rc.make_randoms(rules, n, a.per_core)]
    removal = [c for n in rc.KNOWN for c in rc.removal_cases(rules, n)]
    jobs = [("k", n, le.load(n), sd) for n in rc.KNOWN for sd in seeds] + \
           [("r", i, g["spec"], sd) for i, g in enumerate(groups) for sd in seeds] + \
           [("x", i, c["spec"], sd) for i, c in enumerate(removal) for sd in seeds]

    def run(j):
        kind, _, spec, sd = j
        if kind == "x":
            return rc.run_one(rules, spec, sd, budget=a.budget)
        return rc.run_one(rules, spec, sd, budget=a.budget, opp_level=a.opp_level, max_turn=a.max_turn)
    rows_all = map_ordered(run, jobs, a.workers)
    known = {n: [] for n in rc.KNOWN}
    for g in groups:
        g["rows"] = []
    for c in removal:
        c["rows"] = []
    for (kind, k, _, _), r in zip(jobs, rows_all):
        (known[k] if kind == "k" else groups[k]["rows"] if kind == "r" else removal[k]["rows"]).append(r)
    for n, rows in known.items():
        print(f"既知 {n}: 段2 {rc.rate(rows):.2f}（開始局面 {len({r['start'] for r in rows})} 種）", flush=True)
    randoms = []
    for g in groups:
        n = g.get("combo", "")
        if True:
            print(f"  ランダム {n} {g['old']}→{g['new']} ({'+'.join(rules.cards[x].name for x in g['new'].split('+'))}): 段2 {rc.rate(g['rows']):.2f}", flush=True)
            randoms.append(g)
    rem = rc.judge_removal(removal)
    print("取り除き試験（中核の札1種類を全部抜く）:")
    for x in rem:
        print(f"  {x['combo']} {x['old']}→{x['new']}: 段2 {x['rate']:.2f}"
              f"（定義: {'代わりなし' if x['expected_drop'] else '代わりあり'}）" + (f" ※食い違い: {x['mismatch']}" if x["mismatch"] else ""), flush=True)
    ok, why, summ = rc.judge_control(known, randoms)
    summ["removal"] = rem
    for x in summ["explained"]:
        print(f"  要説明（説明済み {x['label']}、対照から外す）: {x['combo']} {x['old']}→{x['new']} {x['rate']:.2f}")
    for x in summ["pending"]:
        print(f"  要説明（説明なし、保留）: {x['combo']} {x['old']}→{x['new']} {x['rate']:.2f}")
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
