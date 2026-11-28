"""大局観(Plan)つきの順位づけが、段階到達率を上げるかの測定。
天門: 強制3枚(手札)開始・段階目標の鎖を reach_target で順に到達。--plan-w 0 が基準（手で決めた priority のみ）。
使い方: python tools/eval_macro.py --stages data/eval/stages/tenmon.yaml --deck data/decks/tenmon.yaml --seeds 8 --plan-w 0 30"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.search.bestfirst import priority  # noqa: E402
from dmsim.search.reachsearch import reach_target  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.eval.vfeatures import Plan, v_priority  # noqa: E402
from dmsim.plan.macro import load_stage_file  # noqa: E402


def run(rules, deck, stages, seed, plan_w, width, max_turn, force):
    e = Engine.new_game(rules, [deck, ["T001"] * 40], seed, first_player=0)
    for name in force:   # 強制開始: 指定札を山札から手札へ
        c = next((c for c in e.zlist("deck", 0) if e.s.cards[c].defn == name), None)
        if c is not None:
            e._raw_move(c, "hand", controller=0)
    cur, got = e, 0
    for k, tg in enumerate(stages):
        plan = Plan(stages=stages, idx=k)
        prio = (lambda en, me, w, _p=plan: v_priority(en, me, w, priority, plan=_p, plan_w=plan_w)) if plan_w else None
        r = reach_target(cur, tg, 0, width=width, max_turn=max_turn, prio=prio)
        if not r.reached:
            break
        cur, got = r.engine, got + 1
    return got


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", required=True)
    ap.add_argument("--deck", required=True)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--plan-w", type=float, nargs="+", default=[0.0, 30.0])
    ap.add_argument("--width", type=int, default=150)
    ap.add_argument("--max-turn", type=int, default=14)
    ap.add_argument("--force", nargs="*", default=["dm16-007", "dmx19-s06", "dm23bd7-022"])
    a = ap.parse_args(argv)
    rules = load_rules()
    stages, _ = load_stage_file(a.stages)
    from dmsim.cards.decks import load_deck
    deck = load_deck(a.deck)
    for pw in a.plan_w:
        res = [run(rules, deck, stages, sd, pw, a.width, a.max_turn, a.force) for sd in range(1, a.seeds + 1)]
        print(f"plan_w={pw}: 到達段数 {res} 平均 {sum(res)/len(res):.2f} / {len(stages)}", flush=True)


if __name__ == "__main__":
    main()
