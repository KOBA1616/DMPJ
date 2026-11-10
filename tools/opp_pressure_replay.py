"""ドリル・スコール＋ジョバンニ: 相手資源の減少項(opp_pressure)を v_priority に足すと、探索が相手マナを削れるかの測定。
到達不能な目標で reach_target を走らせ、探索中に見えた相手マナの最小値を記録する。使い方: python tools/opp_pressure_replay.py [--w 0 1 3]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim.defs import load_rules  # noqa: E402
from dmsim.discovery.bestfirst import priority  # noqa: E402
from dmsim.discovery.reachsearch import reach_target  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.eval.opp_pressure import make_term  # noqa: E402
from dmsim.eval.vfeatures import v_priority  # noqa: E402

DRILL, JOHANNI = "dm16-051", "dm36-015"


def run(rules, seed, w, width, max_turn, mana_cards):
    e = Engine.new_game(rules, [[DRILL, JOHANNI] + mana_cards * 6 + ["T013"] * 30, ["T001"] * 40], seed, first_player=0)
    pick = lambda d: next(c for c in e.zlist("deck", 0) if e.s.cards[c].defn == d)
    e._raw_move(pick(DRILL), "hand", controller=0)
    e._raw_move(pick(JOHANNI), "bz", controller=0)
    for k in range(6):             # 文明を満たすため、指定の札を交互に置く（片方の文明だけにならないように）
        want = mana_cards[k % len(mana_cards)]
        e._raw_move(next(c for c in e.zlist("deck", 0) if e.s.cards[c].defn == want), "mana", controller=0)
    for o in range(1, 7):          # 相手マナ6
        e._raw_move(e.zlist("deck", 1)[0], "mana", controller=1)
    low = [99]
    term = make_term(mana_w=w) if w else None

    def prio(en, me, wt):
        low[0] = min(low[0], len(en.zlist("mana", 1)))
        return v_priority(en, me, wt, priority, under_w=0, res_w=0, terms=[term] if term else ())
    reach_target(e, {"graveyard": {"*": 99}}, 0, width=width, max_turn=max_turn, prio=prio)
    return low[0]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--w", type=float, nargs="+", default=[0.0, 3.0, 100.0])
    ap.add_argument("--width", type=int, default=100)
    ap.add_argument("--max-turn", type=int, default=6)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--mana", nargs="+", default=["dm16-051", "T013"])
    a = ap.parse_args(argv)
    rules = load_rules()
    for w in a.w:
        res = [run(rules, s, w, a.width, a.max_turn, a.mana) for s in range(1, a.seeds + 1)]
        print(f"mana_w={w}: 探索中の相手マナ最小値 {res}", flush=True)


if __name__ == "__main__":
    main()
