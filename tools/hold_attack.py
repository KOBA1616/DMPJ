#!/usr/bin/env python3
"""攻撃抑制の検証: ミラーで「シールドを割らない」方が得か。

サガ2枚が揃う≒勝利のミラーでは、シールドを割る行為は相手に
手札（＝組み立て用のカード）を与える。殺し切れる時以外は殴らない
方策（hold）が、常時殴る貪欲方策に勝てるかを新レシピで測る。

hold の規則: attack 決定では、相手のシールドが 0 の時だけ攻撃し、
それ以外は pass を選ぶ。それ以外の決定は全て貪欲方策に従う。

使い方: python3 tools/hold_attack.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("DMSIM_RUST", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.ai.demo import greedy_policy  # noqa: E402
from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.engine.loop import LoopDetector  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402


def hold_policy(greedy):
    def pol(eng, d):
        if d.get("kind") == "attack":
            me = d["player"]
            opp_shields = len(eng.s.zones["shield"][1 - me])
            for i, o in enumerate(d["options"]):
                if o.get("key") == "pass" and opp_shields > 0:
                    return [i]
        return greedy(eng, d)
    return pol


def play(rules, deck, seed, pols):
    first = seed % 2
    eng = Engine.new_game(rules, [deck, deck], seed, first_player=first)
    dets = [LoopDetector(me=0, report_all=True),
            LoopDetector(me=1, report_all=True)]
    looped = [False, False]
    breaks = [0, 0]
    for _ in range(2000):
        d = eng.advance()
        if d is None:
            break
        p = d["player"]
        before = len(eng.s.zones["shield"][1 - p])
        eng.answer(pols[p](eng, d))
        after = len(eng.s.zones["shield"][1 - p])
        if after < before:
            breaks[p] += before - after
        if not looped[p] and dets[p].observe(eng) is not None:
            looped[p] = True
        if eng.s.result:
            break
    res = eng.s.result
    if not res or res.get("winner") is None:
        return None
    w = res["winner"]
    return {"winner": w, "loop_win": looped[w],
            "winner_breaks": breaks[w], "loser_breaks": breaks[1 - w]}


def match(rules, deck, name, p0, p1, games, seed0):
    rows = [play(rules, deck, seed0 + i, [p0, p1]) for i in range(games)]
    rows = [r for r in rows if r]
    w = sum(1 for r in rows if r["winner"] == 0)
    lw = sum(1 for r in rows if r["loop_win"])
    print(f"{name}: P0 勝率 {w / len(rows):.2f}（{w}/{len(rows)}）、"
          f"ループ勝ち {lw}、勝者の平均ブレイク "
          f"{sum(r['winner_breaks'] for r in rows) / len(rows):.1f} / "
          f"敗者 {sum(r['loser_breaks'] for r in rows) / len(rows):.1f}")
    return rows


def main() -> int:
    t0 = time.time()
    rules = load_rules()
    deck = load_deck("data/decks/saga.yaml")
    greedy = greedy_policy()
    hold = hold_policy(greedy_policy())
    match(rules, deck, "hold(P0) vs 貪欲", hold, greedy, 20, 0)
    print(f"[{time.time() - t0:.0f}s]", flush=True)
    match(rules, deck, "貪欲(P0) vs hold", greedy, hold, 20, 100)
    print(f"[{time.time() - t0:.0f}s]", flush=True)
    match(rules, deck, "貪欲ミラー（対照）", greedy, greedy, 20, 200)
    print(f"[{time.time() - t0:.0f}s]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
