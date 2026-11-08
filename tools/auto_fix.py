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


def _board(xs):
    board: dict = {}
    for x in xs:
        z, d, *n = x.split(":")
        board.setdefault(z, {})[d] = int(n[0]) if n else 1
    return board


def _prep_ids(combo, rules, deck, opp, spec):
    """準備札: combos.yaml の prep_ids があればそれ、無ければプレイログから自動検出（dmsim.autofix.usage）。"""
    if combo.get("prep_ids"):
        return tuple(combo["prep_ids"])
    from dmsim.autofix.usage import auto_prep_ids
    return auto_prep_ids(rules, deck, opp, spec)


def run_batch(a, combos):
    from dmsim.autofix import run_targets
    ts = yaml.safe_load(Path(a.targets).read_text(encoding="utf-8"))["targets"]
    rules = load_rules()
    specs = load_specs()

    def mk(t):
        from dmsim.autofix.batch import default_board, default_need
        cards = {x.split(":")[0]: int(x.split(":")[1]) if ":" in x else 1 for x in t["need"]} if t.get("need") else default_need(combos[t["combo"]])
        board = _board(t["board"]) if t.get("board") else default_board(combos[t["combo"]])
        spec = yaml.safe_load(Path(t["setup"]).read_text(encoding="utf-8")) if t.get("setup") else None
        deck, opp = load_deck(t["deck"]), load_deck(t["opp_deck"]) if t.get("opp_deck") else ["T001"] * 40
        return harness_measure(rules, deck, opp, list(range(1, t.get("seeds", a.seeds) + 1)), spec,
                               ProgressSpec(board=board, cards=cards) if (cards or board) else None, specs[t["combo"]], max_turn=a.turns, workers=a.workers,
                               prep_ids=_prep_ids(combos[t["combo"]], rules, deck, opp, specs[t["combo"]]))
    for r in run_targets(ts, combos, mk, Rule(turn=a.turns), a.rounds, a.out, a.store):
        print(r)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", help="複数対象のYAML(data/autofix/targets.yaml)。指定時は --combo/--deck 等は無視")
    ap.add_argument("--combo")
    ap.add_argument("--deck")
    ap.add_argument("--setup")
    ap.add_argument("--opp-deck")
    ap.add_argument("--need", nargs="*", default=[])
    ap.add_argument("--board", nargs="*", default=[])
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--store", default="data/autofix/knobs.yaml", help="採用した設定の保存先（次回の開始点になる）")
    ap.add_argument("--workers", type=int, default=1, help="並列プロセス数（seeds を分けて回す。CPU数まで）")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    combos = {c["id"]: c for c in yaml.safe_load(Path("data/known_combos/combos.yaml").read_text(encoding="utf-8"))["combos"]}
    cards = {x.split(":")[0]: int(x.split(":")[1]) if ":" in x else 1 for x in a.need}
    board: dict = {}
    for x in a.board:
        z, d, *n = x.split(":")
        board.setdefault(z, {})[d] = int(n[0]) if n else 1
    if a.targets:
        return run_batch(a, combos)
    spec = yaml.safe_load(Path(a.setup).read_text(encoding="utf-8")) if a.setup else None
    rules_, deck_, opp_ = load_rules(), load_deck(a.deck), load_deck(a.opp_deck) if a.opp_deck else ["T001"] * 40
    meas = harness_measure(rules_, deck_, opp_,
                           list(range(1, a.seeds + 1)), spec, ProgressSpec(board=board, cards=cards) if (cards or board) else None,
                           load_specs()[a.combo], max_turn=a.turns, workers=a.workers, prep_ids=_prep_ids(combos[a.combo], rules_, deck_, opp_, load_specs()[a.combo]))
    k, hist = autofix(meas, Knobs(), combos[a.combo], Rule(turn=a.turns), a.rounds, a.out)
    for h in hist:
        print(h["round"], h["stage"], h["cause"], h["rates"], [(t["change"], t["verdict"]) for t in h.get("tries", [])])
    print("final", k)


if __name__ == "__main__":
    main()
