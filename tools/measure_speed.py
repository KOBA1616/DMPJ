"""エンジン速度の計測（読み取りのみ）。
  python tools/measure_speed.py [--n 200]
(1) 初期化 (2) clone (3) 受動プレイ(全選択=先頭)で 1 ターンの進行 (4) 1人回し探索の局/秒 を測る。"""
import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.cards.defs import load_rules
from dmsim.engine.play import default_decks
from dmsim.engine import Engine
from dmsim.play_api import play_cheat as play_game
from dmsim.engine.view import turn_of  # noqa: E402

def t(f, n):
    s = time.perf_counter()
    for i in range(n): f(i)
    return (time.perf_counter() - s) / n

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=200); a = ap.parse_args()
    rules = load_rules(); deck = default_decks(rules, "dm")[0]; opp = ["T001"] * 40
    print(f"cards loaded: {len(rules.cards)}")
    print(f"new_game: {t(lambda i: Engine.new_game(rules, [deck, deck], i + 1), a.n)*1e3:.2f} ms")
    e = Engine.new_game(rules, [deck, deck], 1); e.advance()
    print(f"clone (initial state): {t(lambda i: e.clone(), a.n)*1e3:.3f} ms")
    def adv(i):
        g = Engine.new_game(rules, [deck, deck], i + 1); n = 0
        while turn_of(g) <= 3 and n < 400:
            d = g.advance()
            if d is None: break
            g.answer(0) if True else None; n += 1
    try: print(f"random-ish play to turn 3 (answer 0): {t(adv, 20)*1e3:.1f} ms/game")
    except Exception as ex: print("passive play failed:", type(ex).__name__, ex)
    s = time.perf_counter(); k = 8
    for i in range(1, k + 1): play_game(rules, deck, opp, i, first_player=i % 2, max_turn=4, budget=200)
    d = time.perf_counter() - s
    print(f"solitaire search (4 turns, budget 200): {k/d:.2f} games/s, {d/k:.2f} s/game")

if __name__ == "__main__":
    main()
