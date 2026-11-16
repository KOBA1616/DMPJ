"""評価ハーネス CLI。 python tools/eval_harness.py --deck X.yaml --seeds 20 --budget-mults 0.5 1 2 [--out report.json]
ログ本体はリポジトリに置かない（--out は logs/ など git 管理外へ）。"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.search.opponent import PRESETS  # noqa: E402
from dmsim.eval.harness import EvalConfig, run_eval  # noqa: E402
from dmsim.eval.infolevel import InfoLevel  # noqa: E402
from dmsim.eval.measure import load_deck  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", required=True, nargs="+")
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--budget", type=int, default=200)
    ap.add_argument("--budget-mults", type=float, nargs="+", default=[1.0])
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--levels", nargs="+", default=["fair", "cheat"], choices=["fair", "cheat"])
    ap.add_argument("--opp", nargs="+", default=["none"], help="相手モデル(dmsim.opponent.PRESETS)。複数で比較")
    ap.add_argument("--opp-deck", help="相手のデッキYAML。省略時は T001×40（bz/blockers/strigger を効かせるには実デッキを指定）")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    cfg = EvalConfig(decks={Path(p).stem: load_deck(p) for p in a.deck}, opp_deck=load_deck(a.opp_deck) if a.opp_deck else ["T001"] * 40, opps={n: PRESETS[n] for n in a.opp},
                     seeds=list(range(1, a.seeds + 1)), levels=tuple(InfoLevel(x) for x in a.levels),
                     budget_mults=tuple(a.budget_mults), base_budget=a.budget, max_turn=a.turns)
    rep = run_eval(load_rules(), cfg)
    txt = json.dumps(rep, ensure_ascii=False, indent=1)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(txt, encoding="utf-8")
    for k, c in rep["cells"].items():
        print(k, {t: round(v["rate"], 3) for t, v in c["kill_rate_by_turn"].items()}, f"nodes={c['mean_nodes']:.0f}")


if __name__ == "__main__":
    main()
