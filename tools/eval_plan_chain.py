"""段階目標の鎖への到達を、plan_w ごとに seed 別に記録する（各段に届いた局数と、届いた通しターン）。
python tools/eval_plan_chain.py --combo tenmon --plan-w 0 30 --seeds 12 [--out logs/plan_chain.jsonl]
force_hand 開始・幅150・14ターン（vgate.chain_score と同じ条件）。plan_w=0 は計画なし。"""
import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.defs import load_rules  # noqa: E402
from dmsim.discovery.reachsearch import reach_chain, reach_graph  # noqa: E402
from dmsim.eval import vgate  # noqa: E402
from dmsim.plan.macro import load_stage_graph, macro_prio  # noqa: E402
from dmsim.solitaire import load_deck  # noqa: E402


def run(combo, pw, seeds, start=1, reserve=0, graph=False, width=150, max_turn=14, targets="data/autofix/targets.yaml"):
    t = next(x for x in yaml.safe_load(Path(targets).read_text(encoding="utf-8"))["targets"] if x["combo"] == combo)
    st = vgate.load_stages(vgate.stage_path(combo))
    stages = [s["target"] for s in st["stages"][1:]]
    keys = list(st["stages"][0]["target"]["hand"])
    rules, deck = load_rules(), load_deck(t["deck"])
    sg = load_stage_graph(vgate.stage_graph_path(combo))[0] if graph else None
    prio = macro_prio(sg if graph else stages, pw, under_w=0, res_w=0) if pw else None
    games = []
    for sd in range(start, seeds + 1):
        e = vgate.start_engine(rules, deck, ["T001"] * 40, keys, sd)
        if e is None:
            continue
        if graph:
            r = reach_graph(e, sg, 0, width=width, max_turn=max_turn, prio=prio, reserve=reserve)
        else:
            r = reach_chain(e, stages, 0, keep_later=True, width=width, max_turn=max_turn, prio=prio, reserve=reserve)
        games.append({"seed": sd, "stages": r["stages"], "turns": r["turns"]})
    n = len(stages) if not graph else len(sg.nodes)
    reached = [sum(1 for g in games if g["stages"] > k) for k in range(n)]    # 段 k 以降に届いた局数
    return {"combo": combo, "plan_w": pw, "n_games": len(games), "n_stages": n, "reached_per_stage": reached,
            "total": sum(g["stages"] for g in games), "reserve": reserve,
            "fastest_turn": {k: min((g["turns"][k] for g in games if g["stages"] > k), default=None) for k in range(n)}, "games": games}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--combo", required=True)
    ap.add_argument("--plan-w", type=float, nargs="+", default=[0.0, 30.0])
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--start", type=int, default=1, help="開始 seed（長い測定を分割して回す用）")
    ap.add_argument("--reserve", type=int, default=0, help="幅のうち次の段に近い局面へ予約する枠（0=なし）")
    ap.add_argument("--graph", action="store_true", help="前提つきの段の集合（<combo>.graph.yaml、tools/gen_stages.py --graph）で reach_graph を使う")
    ap.add_argument("--out", default="logs/plan_chain.jsonl")
    a = ap.parse_args(argv)
    for pw in a.plan_w:
        r = run(a.combo, pw, a.seeds, a.start, a.reserve, a.graph)
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        with open(a.out, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(a.combo, pw, "予約", a.reserve, "局", r["n_games"], "合計", r["total"], "段別", r["reached_per_stage"], flush=True)


if __name__ == "__main__":
    main()
