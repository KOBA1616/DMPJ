"""ターン1の終了局面ごとに「大局観の段の充足率（stage_fraction）」と
「その先で何ターン目に殺せるか」を並べる診断道具。

大局観を保持に接続する実験の材料: 既存の段階目標の鎖（生成チェーン）が、
最速キルに届く局面を上位に置けるか（＝計画の信号がこの局面群を区別できるか）
を測る。比較のため V と順序関数 v2 の順位も併記する。

使い方:
  python tools/plan_leaf_diag.py --setup tests/saga_hidden_setup.yaml --seed 1 \
      --stages-file data/eval/stages/saga.generated.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

from dmsim import load_rules  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from dmsim.plan.macro import MacroPlanner, load_stage_file, stage_fraction  # noqa: E402
from dmsim.search import turn  # noqa: E402
from dmsim.search.leaf_eval import evaluate  # noqa: E402
from exhaustive_proto import STAGES, _make_stage_search, stage_candidates  # noqa: E402
from exhaustive_crossturn import LeafCollector, advance_to_my_turn  # noqa: E402
from order_fn import ruler_key  # noqa: E402

DRAG = "dm22ex1-007"


def zone_counts(eng, p=0):
    z = eng.s.zones
    return {name: len(z[name][p]) for name in ("hand", "mana", "graveyard", "bz", "shield", "deck")}


def outcome_from(rules, search_cls, start_eng, max_turn, budget):
    """start_eng（自分のターン開始局面）から frontier で進め、最速キルターンを返す。"""
    frontier = [start_eng]
    for t in range(2, max_turn + 1):
        nxt: dict[str, tuple[float, object]] = {}
        for e0 in frontier:
            ts = search_cls(0, budget=budget)
            lv, _tr, _n = LeafCollector(ts).collect(e0, budget)
            for v2, leaf, _l in lv:
                r = leaf.s.result
                if r is not None and r.get("winner") == 0:
                    return t
                ne = advance_to_my_turn(leaf)
                if ne is not None:
                    k = ne.s.fast_key()
                    if k not in nxt or v2 > nxt[k][0]:
                        nxt[k] = (v2, ne)
        if not nxt:
            return None
        frontier = [e for _v, e in sorted(nxt.values(), key=lambda x: -x[0])[:64]]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", default="tests/saga_hidden_setup.yaml")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--max-turn", type=int, default=3)
    ap.add_argument("--stage", type=int, default=1)
    ap.add_argument("--budget", type=int, default=200_000)
    ap.add_argument("--stages-file", default="data/eval/stages/saga.generated.yaml")
    a = ap.parse_args()

    rules = load_rules()
    print("rules loaded", flush=True)
    stages, _goal = load_stage_file(a.stages_file)
    planner = MacroPlanner(stages=stages)
    print(f"stages: {len(stages)} from {a.stages_file}", flush=True)

    setup0 = yaml.safe_load(Path(a.setup).read_text(encoding="utf-8"))
    setup = dict(setup0, seed=a.seed)
    st = next(s for s in STAGES if s["stage"] == a.stage)
    fn, _label = stage_candidates("rank", a.stage)
    orig = turn.candidates
    turn.candidates = fn
    try:
        search_cls = _make_stage_search(st["stock_offsets"])
        start = sc.build(rules, setup)
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
                key = nxt.s.fast_key()
                if key not in states or v > states[key][0]:
                    states[key] = (v, nxt)
        print(f"turn1 end states: {len(states)}", flush=True)

        rows = []
        for v, eng in states.values():
            plan = planner.plan(eng, 0)
            frac = stage_fraction(eng, 0, plan)
            kt = outcome_from(rules, search_cls, eng, a.max_turn, a.budget)
            zc = zone_counts(eng)
            drag_in_hand = any(eng.s.cards[c].defn == DRAG for c in eng.s.zones["hand"][0])
            rows.append({"frac": frac, "idx": plan.idx, "intent": plan.intent, "V": v,
                         "ruler": ruler_key(eng, 0), "kill_turn": kt, "zones": zc,
                         "drag": drag_in_hand})
        by_frac = sorted(rows, key=lambda r: -r["frac"])
        by_v = sorted(rows, key=lambda r: -r["V"])
        by_ruler = sorted(rows, key=lambda r: r["ruler"], reverse=True)
        rank_of = {id(r): i for i, r in enumerate(by_frac)}
        vrank_of = {id(r): i for i, r in enumerate(by_v)}
        rrank_of = {id(r): i for i, r in enumerate(by_ruler)}
        print(f"{'frac-rank':>9} {'fraction':>8} {'段idx':>5} {'V-rank':>6} {'ruler-rank':>10} "
              f"{'kill_turn':>9} {'DRAG手札':>7}  zones(h/m/g/b/s/d)")
        for r in by_frac:
            z = r["zones"]
            print(f"{rank_of[id(r)]:>9} {r['frac']:>8.3f} {r['idx']:>5} {vrank_of[id(r)]:>6} "
                  f"{rrank_of[id(r)]:>10} {str(r['kill_turn']):>9} {str(r['drag']):>7}  "
                  f"{z['hand']}/{z['mana']}/{z['graveyard']}/{z['bz']}/{z['shield']}/{z['deck']}")
        kills = [r for r in rows if r["kill_turn"] is not None]
        if kills:
            fastest = min(r["kill_turn"] for r in kills)
            fr = [r for r in kills if r["kill_turn"] == fastest]
            print(f"fastest kill turn={fastest}: frac-rank {sorted(rank_of[id(r)] for r in fr)}, "
                  f"V-rank {sorted(vrank_of[id(r)] for r in fr)}, "
                  f"ruler-rank {sorted(rrank_of[id(r)] for r in fr)}", flush=True)
            print(f"distinct fraction values: {sorted({round(r['frac'], 3) for r in rows})}", flush=True)
    finally:
        turn.candidates = orig


if __name__ == "__main__":
    main()
