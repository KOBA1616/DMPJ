"""リソース型の目盛りの分布（docs/combo-ruler-design.md §15）: 既知（騎士＋DMC）と、中核1種類だけ差し替えたランダム組。
  python tools/resource_dist.py [--seeds 8] [--per-core 4] [--out data/eval/resource_dist.json]"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dmsim import load_rules  # noqa: E402
from dmsim.eval import resource as rs  # noqa: E402
from dmsim.eval.ruler_control import candidates, core_ids  # noqa: E402

SETUP = "data/registry/setups/knight_dmc.json"
CORE = ("dm25ex3-028", "dm25ex3-055")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--per-core", type=int, default=4)
    ap.add_argument("--out", default="data/eval/resource_dist.json")
    a = ap.parse_args(argv)
    rules = load_rules()
    spec, deck = rs.load_setup(SETUP)
    seeds = list(range(1, a.seeds + 1))
    groups = [{"combo": "knight_dmc", "old": None, "new": None, "spec": spec, "deck": deck}]
    rng = random.Random("knight_dmc:0")
    for old in CORE:
        for new in rng.sample(candidates(rules, old, core_ids()), a.per_core):
            s2, d2 = rs.swap(spec, deck, old, new)
            groups.append({"combo": "random", "old": old, "new": new, "spec": s2, "deck": d2})
    out = []
    for g in groups:
        rows = [rs.measure_one(rules, g["spec"], g["deck"], s) for s in seeds]
        summ = rs.summarize(rows)
        out.append({k: g[k] for k in ("combo", "old", "new")} | summ | {"rows": rows})
        print(g["combo"], g["old"], "->", g["new"], summ, flush=True)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
