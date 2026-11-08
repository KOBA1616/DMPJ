"""キルが出ない原因の自動診断→改善→再測定。 python tools/auto_fix.py --combo saga --setup tests/saga_setup.yaml --need DEFN:1 --board graveyard:DEFN:1 --out logs/autofix.jsonl
検証専用(holdout)のコンボは拒否する。履歴は --out に追記（版つき規則 v0）。"""
import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.autofix import Knobs, Rule, autofix, harness_measure  # noqa: E402
from dmsim.defs import load_rules  # noqa: E402
from dmsim.eval.progress import ProgressSpec  # noqa: E402
from dmsim.search.leaf_parts import load_specs  # noqa: E402
from dmsim.solitaire import load_deck  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--combo", required=True)
    ap.add_argument("--deck", required=True)
    ap.add_argument("--setup")
    ap.add_argument("--opp-deck")
    ap.add_argument("--need", nargs="*", default=[])
    ap.add_argument("--board", nargs="*", default=[])
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    combos = {c["id"]: c for c in yaml.safe_load(Path("data/known_combos/combos.yaml").read_text(encoding="utf-8"))["combos"]}
    cards = {x.split(":")[0]: int(x.split(":")[1]) if ":" in x else 1 for x in a.need}
    board: dict = {}
    for x in a.board:
        z, d, *n = x.split(":")
        board.setdefault(z, {})[d] = int(n[0]) if n else 1
    spec = yaml.safe_load(Path(a.setup).read_text(encoding="utf-8")) if a.setup else None
    meas = harness_measure(load_rules(), load_deck(a.deck), load_deck(a.opp_deck) if a.opp_deck else ["T001"] * 40,
                           list(range(1, a.seeds + 1)), spec, ProgressSpec(board=board, cards=cards) if (cards or board) else None,
                           load_specs()[a.combo], max_turn=a.turns)
    k, hist = autofix(meas, Knobs(), combos[a.combo], Rule(turn=a.turns), a.rounds, a.out)
    for h in hist:
        print(h["round"], h["stage"], h["cause"], h["rates"], [(t["change"], t["verdict"]) for t in h.get("tries", [])])
    print("final", k)


if __name__ == "__main__":
    main()
