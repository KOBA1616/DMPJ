"""複数ターン探索の前後比較（公平探索のみ・同一シード）。
python tools/eval_multiturn.py --setup tests/saga_prep_setup.yaml --seeds 100 --turns 4 --lookahead 20 [--seed-from 1] [--out x.json]
A=lookahead 0（従来）, B=lookahead N。各シードを両方で回し、キル率と対比較(paired_diff)を出す。"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.eval import fair_runner  # noqa: E402
from dmsim.eval.harness import EvalConfig, compare, run_eval  # noqa: E402
from dmsim.eval.infolevel import InfoLevel  # noqa: E402
from dmsim.search.opponent import PRESETS  # noqa: E402
from dmsim.engine.play import default_decks  # noqa: E402
from dmsim.eval.measure import load_deck  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=100)
    ap.add_argument("--seed-from", type=int, default=1)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--budget", type=int, default=100)
    ap.add_argument("--n-det", type=int, default=4)
    ap.add_argument("--lookahead", type=int, default=20)
    ap.add_argument("--deck", help="デッキYAML。省略時は default_decks の1番目")
    ap.add_argument("--setup", help="scenario YAML（開始局面）")
    ap.add_argument("--opp", default="none")
    ap.add_argument("--opp-deck")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    import yaml
    rules = load_rules()
    deck = load_deck(a.deck) if a.deck else default_decks(rules, "dm")[0]
    spec = yaml.safe_load(Path(a.setup).read_text(encoding="utf-8")) if a.setup else None
    reps = {}
    for name, la in (("before", 0), ("after", a.lookahead)):
        fair_runner.register(a.n_det, la)
        cfg = EvalConfig(levels=(InfoLevel.FAIR,), n_det=a.n_det, start_spec=spec, decks={"d": deck},
                         opp_deck=load_deck(a.opp_deck) if a.opp_deck else ["T001"] * 40, opps={a.opp: PRESETS[a.opp]},
                         seeds=list(range(a.seed_from, a.seed_from + a.seeds)), base_budget=a.budget, max_turn=a.turns)
        reps[name] = run_eval(rules, cfg)
    key = next(iter(reps["before"]["cells"]))
    out = {"key": key, "turns": {}}
    for name, rep in reps.items():
        c = rep["cells"][key]
        print(name, {t: round(v["rate"], 3) for t, v in c["kill_rate_by_turn"].items()}, f"nodes={c['mean_nodes']:.0f} sec={c['seconds']:.0f}")
        out[name] = {"kill_rate_by_turn": c["kill_rate_by_turn"], "mean_nodes": c["mean_nodes"], "seconds": c["seconds"], "per_game": c["per_game"]}
    for t in range(1, a.turns + 1):
        d = compare(reps["after"], reps["before"], key, t)   # after - before
        out["turns"][t] = d
        print("diff(after-before) turn", t, round(d["diff"], 3), [round(x, 3) for x in d["ci"]], "sig" if d["significant"] else "")
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
