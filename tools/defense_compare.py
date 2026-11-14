"""相手のターン中の防御（dmsim.search.defense）の有効・無効の比較。
python tools/defense_compare.py --games 20 --levels 2a 2b --decks saga akashic blocker --workers 4
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _deck(name):
    from dmsim.eval.measure import load_deck
    from dmsim.search.opponent import RESIST_CONTROL, RESIST_TRIGGERS
    if name == "blocker":      # 対照: 相手 2b と同じ光・水のブロッカー中心＋トリガー
        body = list(RESIST_CONTROL) + list(RESIST_TRIGGERS[-2:])
        return sorted(body[i % len(body)] for i in range(40))
    return load_deck(f"data/decks/{name}.yaml")


def _one(args):
    deck, level, seed, on, budget, n_det = args
    from dmsim.search import defense
    defense.set_enabled(on)
    from dmsim.cards.defs import load_rules
    from dmsim.eval import attack
    rules = load_rules()
    r = attack.run_one(rules, _deck(deck), seed, opp_level=level, max_turn=6, budget=budget, n_det=n_det)
    return deck, level, on, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--levels", nargs="+", default=["2a", "2b"])
    ap.add_argument("--decks", nargs="+", default=["saga", "akashic", "blocker"])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--budget", type=int, default=200)
    ap.add_argument("--n-det", type=int, default=8)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    jobs = [(d, lv, s, on, a.budget, a.n_det) for d in a.decks for lv in a.levels for on in (False, True) for s in range(a.games)]
    rows = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for deck, lv, on, r in ex.map(_one, jobs):
            rows.setdefault((deck, lv, on), []).append(r)
    out = []
    for (deck, lv, on), rs in sorted(rows.items(), key=lambda x: str(x[0])):
        n = len(rs)
        lost = [r for r in rs if r.get("lost")]
        k = lambda t: sum(1 for r in rs if r["kill_turn"] is not None and r["kill_turn"] <= t)
        row = {"deck": deck, "opp": lv, "defend": on, "games": n, "lost": len(lost),
               "lost_by5": sum(1 for r in lost if (r.get("lost_turn") or 99) <= 5), "win4": k(4), "win6": k(6),
               "errors": sum(1 for r in rs if r["error"])}
        out.append(row)
        print(json.dumps(row, ensure_ascii=False))
    if a.out:
        json.dump(out, open(a.out, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
