"""横断探索との比較用: 従来方式（game.play_game のターン毎・最良線確定）を
シナリオ配置から回すベースライン。exhaustive_crossturn と同じ段・順序で測る。

使い方:
  python tools/greedy_scenario_baseline.py --setup tests/saga_prep_setup.yaml --seeds 1,2,3 --max-turn 4
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
from dmsim.search import game, turn  # noqa: E402
from exhaustive_proto import STAGES, _make_stage_search, stage_candidates  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", default="tests/saga_prep_setup.yaml")
    ap.add_argument("--seeds", default="1")
    ap.add_argument("--max-turn", type=int, default=4)
    ap.add_argument("--stage", type=int, default=1)
    ap.add_argument("--order", default="rank", choices=["rank", "canonical", "value"])
    ap.add_argument("--value-fn", default="value", choices=["value", "ruler"],
                    help="TurnSearch の葉評価を差し替える（ruler=順序関数）")
    ap.add_argument("--budget", type=int, default=200_000)
    a = ap.parse_args()
    from order_fn import make_value_fn
    vfn = make_value_fn(a.value_fn)

    rules = load_rules()
    print("rules loaded", flush=True)
    setup0 = yaml.safe_load(Path(a.setup).read_text(encoding="utf-8"))
    st = next(s for s in STAGES if s["stage"] == a.stage)
    fn, _label = stage_candidates(a.order, a.stage)
    orig_c, orig_ts = turn.candidates, game.TurnSearch
    turn.candidates = fn
    game.TurnSearch = _make_stage_search(st["stock_offsets"])
    try:
        for seed in [int(s) for s in a.seeds.split(",") if s.strip()]:
            setup = dict(setup0)
            setup["seed"] = seed
            eng = sc.build(rules, setup)
            t0 = time.perf_counter()
            res, _final = game.play_game(rules, None, None, seed, max_turn=a.max_turn,
                                         budget=a.budget, lock_rounds=0, start=eng, value_fn=vfn)
            verdict = "kill" if res.kind else ("lost" if res.lost else "no-kill")
            print(f"[{Path(a.setup).stem} seed{seed} greedy] {verdict.upper()} "
                  f"kill_turn={res.kill_turn} kind={res.kind} nodes={res.nodes} "
                  f"error={res.error} wall={time.perf_counter() - t0:.1f}s", flush=True)
    finally:
        turn.candidates, game.TurnSearch = orig_c, orig_ts


if __name__ == "__main__":
    main()
