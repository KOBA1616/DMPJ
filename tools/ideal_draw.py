"""既知コンボの「理想の引き」の上限の近似（2026-11-13）。

山札の並びが見える探索（CHEAT、play_game）で、通常の開幕（マナ0）から多数の並び（シード）を回し、最速の勝ちを取る。
並びを最適化するのではなく、シードごとの並びの中で最も都合のよいものを拾う近似（上限の下側の見積もり）。
相手は無抵抗（マナチャージだけ）。勝ち方は origin で loop / engine / combat / effect / lock に分けて記録する。
使い方: python tools/ideal_draw.py <deck.yaml> <seed_lo> <seed_hi> [budget] [max_turn] > out.jsonl
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dmsim.cards.decks import load_deck  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.eval.lockcheck import lock_probe  # noqa: E402
from dmsim.play_api import play_cheat as play_game  # noqa: E402


def main():
    deck_path, lo, hi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    budget = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
    max_turn = int(sys.argv[5]) if len(sys.argv) > 5 else 4
    rules = load_rules()
    deck = load_deck(deck_path)
    for seed in range(lo, hi):
        for first in (0, 1):
            res, eng = play_game(rules, deck, ["T001"] * 40, seed, first_player=first, max_turn=max_turn,
                                 budget=budget, lock_judge=lock_probe)
            z = eng.s.zones
            end = {"mana": len(z["mana"][0]), "hand": len(z["hand"][0]), "deck": len(z["deck"][0]),
                   "gy_creatures": sum(1 for c in z["graveyard"][0] if eng.cdef(c).is_creature()),
                   "bz": [eng.s.cards[c].defn for c in z["bz"][0]]}
            line = [x["keys"] for x in eng.log if x["p"] == 0 and x["kind"] in ("main", "charge", "attack")] if res.kill_turn else None
            print(json.dumps({"seed": seed, "first": first, "kill_turn": res.kill_turn, "kind": res.kind, "origin": res.origin,
                              "loops": [{k: lp.get(k) for k in ("source", "win_by", "laps")} for lp in res.loops],
                              "end": end, "line": line, "error": res.error}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
