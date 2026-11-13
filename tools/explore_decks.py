"""実カードの山からランダムなデッキを作り、1人回しでループ／ロック由来のキルが出るデッキを探す（ステップ4の入口）。

  python tools/explore_decks.py --decks 200 --games 4 --turns 5 --budget 100 --workers 4 --out found.json
各デッキは 40 枚（同名最大 4 枚）。ループを1度でもストックした、またはロックが成立した局のあるデッキを集計する。
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.eval.measure import measure  # noqa: E402


def random_deck(ids: list[str], rng: random.Random, size: int = 40, kinds: int = 14) -> list[str]:
    pool = rng.sample(ids, min(kinds, len(ids)))
    deck: list[str] = []
    while len(deck) < size:
        c = rng.choice(pool)
        if deck.count(c) < 4:
            deck.append(c)
    return deck


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--decks", type=int, default=100)
    ap.add_argument("--games", type=int, default=4, help="デッキごとの seed 数")
    ap.add_argument("--turns", type=int, default=5)
    ap.add_argument("--budget", type=int, default=100)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    rules = load_rules()
    ids = sorted(c for c in rules.cards if not c.startswith(("T", "R", "L")))
    rng = random.Random(a.seed)
    found = []
    for i in range(a.decks):
        deck = random_deck(ids, rng)
        rs = measure(deck, ["T001"] * 40, range(1, a.games + 1), rules=rules, workers=a.workers,
                     max_turn=a.turns, budget=a.budget)
        kills = [r for r in rs if r.kill_turn is not None]
        loops = [r for r in rs if r.loops]
        errs = [r for r in rs if r.error]
        if kills or loops or errs:
            found.append({"deck": deck, "kills": [[r.seed, r.first_player, r.kill_turn, r.kind, r.origin] for r in kills],
                          "loops": [lp for r in loops for lp in r.loops][:3], "errors": [r.error for r in errs][:2]})
            print(f"[{i}] kills={len(kills)} loops={len(loops)} errors={len(errs)}", flush=True)
    print(f"{len(found)}/{a.decks} decks with kills/loops/errors")
    if a.out:
        Path(a.out).write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
