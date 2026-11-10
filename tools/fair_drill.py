"""公平探索（相手の山札を見ない）で、ドリル＋ジョバンニの通常開幕から相手マナ破壊に届くかの測定。
葉の評価に opp_pressure を足した版と足さない版を比べる。使い方: python tools/fair_drill.py --seeds 6 --turns 12 --budget 200 --n-det 4"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.engine_view import active_of, result_of  # noqa: E402
from dmsim.eval.opp_pressure import opp_pressure  # noqa: E402
from dmsim.search.fair import FairTurnSearch  # noqa: E402
from dmsim.solitaire import Weights, charge_only_policy, evaluate, own_turn  # noqa: E402

D, J = "dm16-051", "dm36-015"


def run(rules, seed, use_term, turns, budget, n_det, copies, filler="T001"):
    deck = [D] * copies + [J] * copies + [filler] * (40 - 2 * copies)
    eng = Engine.new_game(rules, [deck, ["T001"] * 40], seed, first_player=0)
    w = Weights()
    vf = (lambda e, me: evaluate(e, me, w) + opp_pressure(e, me)) if use_term else None
    low, dk = 6, 40
    while (d := eng.advance()) is not None:
        if active_of(eng) != 0 or d["player"] != 0:
            eng.answer(charge_only_policy(eng, d))
            continue
        if own_turn(eng, 0) > turns:
            break
        eng = FairTurnSearch(0, budget, n_det, seed * 7919 + own_turn(eng, 0), value_fn=vf).run(eng)
        low = min(low, len(eng.zlist("mana", 1)))
        dk = min(dk, len(eng.zlist("deck", 1)))
    return low, dk, result_of(eng)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--turns", type=int, default=6, help="自分のターン数")
    ap.add_argument("--budget", type=int, default=200)
    ap.add_argument("--n-det", type=int, default=4)
    ap.add_argument("--filler", default="T001", help="穴埋めカード（既定は効果なしのダミー）")
    ap.add_argument("--copies", type=int, default=4)
    a = ap.parse_args(argv)
    rules = load_rules()
    for use in (False, True):
        res = []
        for s in range(1, a.seeds + 1):
            low, dk, r = run(rules, s, use, a.turns, a.budget, a.n_det, a.copies, a.filler)
            res.append(low)
            print(f"  term={use} seed={s} 相手マナ最小={low} 相手山札最小={dk} 結果={r}", flush=True)
        print(f"[公平] opp_pressure={'あり' if use else 'なし'}: 相手マナ最小値 {res}", flush=True)


if __name__ == "__main__":
    main()
