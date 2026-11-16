"""ターン1の終了局面ごとに「その先で何ターン目に殺せるか」を測る道具。

順序関数の設計材料: 貪欲方式が V 最大で選ぶターン1の葉が、最速キルに
つながる葉とどれだけズレているか（順序の損失）を数値で出す。

使い方:
  python tools/turn1_leaf_outcomes.py --setup tests/saga_hidden_setup.yaml --seed 1 --max-turn 3
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

from dmsim import load_rules  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from dmsim.search import turn  # noqa: E402
from dmsim.search.leaf_eval import evaluate  # noqa: E402
from exhaustive_proto import STAGES, _make_stage_search, stage_candidates  # noqa: E402
from exhaustive_crossturn import LeafCollector, advance_to_my_turn  # noqa: E402


def zone_counts(eng, p=0):
    z = eng.s.zones
    return {name: len(z[name][p]) for name in ("hand", "mana", "graveyard", "bz", "shield", "deck")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", default="tests/saga_hidden_setup.yaml")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--max-turn", type=int, default=3)
    ap.add_argument("--stage", type=int, default=1)
    ap.add_argument("--budget", type=int, default=200_000)
    a = ap.parse_args()

    rules = load_rules()
    print("rules loaded", flush=True)
    setup0 = yaml.safe_load(Path(a.setup).read_text(encoding="utf-8"))
    setup = dict(setup0, seed=a.seed)
    st = next(s for s in STAGES if s["stage"] == a.stage)
    fn, _label = stage_candidates("rank", a.stage)
    orig = turn.candidates
    turn.candidates = fn
    try:
        search_cls = _make_stage_search(st["stock_offsets"])
        start = sc.build(rules, setup)

        # ターン1の葉を集め、次の自分の決定点で重複排除する
        ts = search_cls(0, budget=a.budget)
        leaves, trunc, nodes = LeafCollector(ts).collect(start, a.budget)
        print(f"turn1: leaves={len(leaves)} nodes={nodes} truncated={trunc}", flush=True)
        states: dict[str, tuple[float, object]] = {}
        for v, leaf, _loops in leaves:
            r = leaf.s.result
            if r is not None and r.get("winner") == 0:
                print("turn1 KILL leaf exists", flush=True)
                return
            nxt = advance_to_my_turn(leaf)
            if nxt is not None:
                key = nxt.s.digest()
                if key not in states or v > states[key][0]:
                    states[key] = (v, nxt)
        print(f"turn1 end states: {len(states)}", flush=True)

        rows = []
        for v, st_eng in states.values():
            kill_turn = None
            frontier = [st_eng]
            capped = False
            for t in range(2, a.max_turn + 1):
                nxt: dict[str, tuple[float, object]] = {}
                for e0 in frontier:
                    ts2 = search_cls(0, budget=a.budget)
                    lv, tr, _n = LeafCollector(ts2).collect(e0, a.budget)
                    capped = capped or tr
                    for v2, leaf, _l in lv:
                        r = leaf.s.result
                        if r is not None and r.get("winner") == 0:
                            kill_turn = t
                            break
                        ne = advance_to_my_turn(leaf)
                        if ne is not None:
                            k = ne.s.digest()
                            if k not in nxt or v2 > nxt[k][0]:
                                nxt[k] = (v2, ne)
                    if kill_turn:
                        break
                if kill_turn or not nxt:
                    break
                states2 = sorted(nxt.values(), key=lambda x: -x[0])[:64]
                frontier = [e for _v, e in states2]
            rows.append((v, kill_turn, zone_counts(st_eng)))
        rows.sort(key=lambda x: -x[0])
        print(f"{'V-rank':>6} {'V':>9} {'kill_turn':>9}  zones(hand/mana/grave/bz/shield/deck)")
        for i, (v, kt, zc) in enumerate(rows):
            print(f"{i:>6} {v:>9.0f} {str(kt):>9}  {zc['hand']}/{zc['mana']}/{zc['graveyard']}/{zc['bz']}/{zc['shield']}/{zc['deck']}")
        kills = [(i, kt) for i, (_v, kt, _z) in enumerate(rows) if kt is not None]
        if kills:
            best_rank = min(i for i, _kt in kills)
            fastest = min(kt for _i, kt in kills)
            fast_rank = min(i for i, kt in kills if kt == fastest)
            print(f"fastest kill turn={fastest}: best V-rank among fastest-kill states = {fast_rank} "
                  f"(greedy picks rank 0; rank 0 kill_turn = {rows[0][1]})", flush=True)
    finally:
        turn.candidates = orig


if __name__ == "__main__":
    main()
