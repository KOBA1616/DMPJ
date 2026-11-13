"""ベンチマーク: 1人回しの局数/秒と cProfile の上位を出す。
  python tools/bench.py [--games 6] [--budget 200] [--turns 4] [--profile]
seed 固定で決定的なので、高速化の前後で results が一致するはず。"""
import argparse
import cProfile
import pstats
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.play import default_decks  # noqa: E402
from dmsim.search.game import play_game  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=6)
    ap.add_argument("--budget", type=int, default=200)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--prefix", default="dm", help="デッキに使うカード ID の接頭辞（既定 dm = 実カード）")
    ap.add_argument("--profile", action="store_true")
    a = ap.parse_args()
    rules = load_rules()
    deck = default_decks(rules, a.prefix)[0]
    opp = ["T001"] * 40

    def run():
        out = []
        for s in range(1, a.games + 1):
            res, _ = play_game(rules, deck, opp, s, first_player=s % 2, max_turn=a.turns, budget=a.budget)
            out.append((res.kill_turn, res.kind))
        return out

    t = time.perf_counter()
    if a.profile:
        pr = cProfile.Profile()
        out = pr.runcall(run)
        pstats.Stats(pr).sort_stats("tottime").print_stats(18)
    else:
        out = run()
    dt = time.perf_counter() - t
    print(f"{a.games} games in {dt:.2f}s = {a.games / dt:.2f} games/s; results={out}")


if __name__ == "__main__":
    main()
