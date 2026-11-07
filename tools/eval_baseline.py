"""ベースライン分散と隠れ情報コストの測定。 python tools/eval_baseline.py [--seeds 10] [--budget 100] [--n-det 4] [--out logs/baseline.json]
default_decks(prefix) の1番目のデッキを、同一シードで FAIR と CHEAT で回し、対比較を出す。"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.defs import load_rules  # noqa: E402
from dmsim.eval import fair_runner  # noqa: E402
from dmsim.eval.harness import EvalConfig, hidden_info_cost, run_eval  # noqa: E402
from dmsim.play import default_decks  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--budget", type=int, default=100)
    ap.add_argument("--n-det", type=int, default=4)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--prefix", default="dm")
    ap.add_argument("--deck", nargs="*", help="デッキYAML(load_deck形式)。複数可。省略時は default_decks の1番目")
    ap.add_argument("--setup", help="scenario YAML（キル手前の局面から始める。例 tests/saga_setup.yaml）")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    rules = load_rules()
    fair_runner.register(a.n_det)
    from dmsim.solitaire import load_deck
    decks = {Path(p).stem: load_deck(p) for p in a.deck} if a.deck else {"default0": default_decks(rules, a.prefix)[0]}
    import yaml
    spec = yaml.safe_load(Path(a.setup).read_text(encoding="utf-8")) if a.setup else None
    cfg = EvalConfig(start_spec=spec, decks=decks, opp_deck=["T001"] * 40, seeds=list(range(1, a.seeds + 1)),
                     base_budget=a.budget, max_turn=a.turns)
    rep = run_eval(rules, cfg)
    rep["hidden_info_cost"] = {d: {t: hidden_info_cost(rep, d, t) for t in range(1, a.turns + 1)} for d in decks}
    for k, c in rep["cells"].items():
        print(k, {t: [round(v["rate"], 2), [round(x, 2) for x in v["ci95"]]] for t, v in c["kill_rate_by_turn"].items()},
              f"nodes={c['mean_nodes']:.0f} sec={c['seconds']:.0f}")
    for d, ts in rep["hidden_info_cost"].items():
        for t, v in ts.items():
            print("cost", d, "turn", t, round(v["diff"], 3), [round(x, 3) for x in v["ci"]], "sig" if v["significant"] else "")
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
