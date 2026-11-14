"""高速化の前後で結果が完全に一致するかを見るための指紋（全決定の記録のハッシュ）。
python tools/same_seed_check.py > out.txt  （前後で out.txt を diff する）"""
from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CASES = [("saga", 0, s) for s in range(3)] + [("akashic", "2a", s) for s in range(2)] + [("saga", "2b", s) for s in range(2)] \
    + [("knight_dmc", 1, 0)]


def main():
    from dmsim.cards.defs import load_rules
    from dmsim.eval import assemble
    from dmsim.base.loopspec import LoopSpec
    from dmsim.eval.measure import load_deck
    rules = load_rules()
    ls = LoopSpec(name="attack", kind="deterministic", minimal=[])
    for deck, lv, seed in CASES:
        hold = {}
        r = assemble.run_one(rules, ls, seed, deck=load_deck(f"data/decks/{deck}.yaml"), max_turn=5, budget=200, n_det=8,
                             opp_level=lv, trace=lambda e, t: hold.__setitem__("e", e))
        log = hold["e"].log if "e" in hold else []
        h = hashlib.sha1(json.dumps(log, sort_keys=True, default=str).encode()).hexdigest()[:16]
        res = r["res"]
        print(deck, lv, seed, len(log), h, res.kill_turn, res.lost, res.nodes, flush=True)


if __name__ == "__main__":
    main()
