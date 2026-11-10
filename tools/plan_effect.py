"""計画項が順位づけを実際に変えているかを測る。 python tools/plan_effect.py --combo saga --seeds 3 --plan-w 3 [--width 40]
探索中に呼ばれた全局面の (基本の順位づけ, 基本+計画項) を集め、無作為な局面の対で大小が入れ替わる割合と、計画項が 0 でない局面の割合を出す。
入れ替わりがほぼ 0 なら、計画項は（その plan_w では）探索に効いていない。"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.defs import load_rules  # noqa: E402
from dmsim.discovery.bestfirst import priority  # noqa: E402
from dmsim.discovery.reachsearch import reach_chain  # noqa: E402
from dmsim.eval import vgate  # noqa: E402
from dmsim.plan.macro import MacroPlanner, stage_fraction  # noqa: E402
from dmsim.solitaire import load_deck  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--combo", default="tenmon")
    ap.add_argument("--targets", default="data/autofix/targets.yaml")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--plan-w", type=float, default=3.0)
    ap.add_argument("--width", type=int, default=40)
    a = ap.parse_args(argv)
    t = next(x for x in yaml.safe_load(Path(a.targets).read_text(encoding="utf-8"))["targets"] if x["combo"] == a.combo)
    st = vgate.load_stages(vgate.stage_path(a.combo))
    stages = [s["target"] for s in st["stages"][1:]]
    keys = list(st["stages"][0]["target"]["hand"])
    rules, deck = load_rules(), load_deck(t["deck"])
    planner = MacroPlanner(stages)
    rec: list[tuple[float, float]] = []

    def prio(eng, me, w):
        b = priority(eng, me, w)
        p = a.plan_w * stage_fraction(eng, me, planner.plan(eng, me))
        rec.append((b, p))
        return b + p

    for sd in range(1, a.seeds + 1):
        e = vgate.start_engine(rules, deck, ["T001"] * 40, keys, sd)
        if e is not None:
            reach_chain(e, stages, 0, keep_later=True, lookahead=2, width=a.width, max_depth=80, max_turn=14, prio=prio)
    rnd = random.Random(0)
    n, flips, nonzero = len(rec), 0, sum(1 for _, p in rec if p)
    pairs = 20000
    for _ in range(pairs):
        (b1, p1), (b2, p2) = rnd.choice(rec), rnd.choice(rec)
        if (b1 - b2) * ((b1 + p1) - (b2 + p2)) < 0:
            flips += 1
    print(f"{a.combo} plan_w={a.plan_w} 局面{n} 計画項が0でない割合={nonzero / n:.3f} 無作為な対で順位が入れ替わる割合={flips / pairs:.3f}")


if __name__ == "__main__":
    main()
