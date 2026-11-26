#!/usr/bin/env python3
"""対戦内容の検証: 方策ごとに「何ターンで・どうやって」勝つか。

Phase 1 ベンチの「平均 20.4 ターン」はランダム方策の数字だった。
まともな方策（学習済み・貪欲・探索）では何ターンで決着し、
サガループは実際に回って勝ち切るのかを実測する。

記録: 勝者 / 終了理由（result.reason）/ 総ターン数 / 勝者の自ターン数 /
ループ検出（LoopDetector、勝者側で最初に検出された自ターン数）。

使い方: python3 tools/game_content.py
"""
from __future__ import annotations

import os
import sys
import time
from collections import Counter
from pathlib import Path

os.environ.setdefault("DMSIM_RUST", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np  # noqa: E402

from dmsim.ai.demo import greedy_policy, model_policy  # noqa: E402
from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.engine.loop import LoopDetector  # noqa: E402
from dmsim.engine.play import random_policy  # noqa: E402
from dmsim.search.turn import TurnSearch  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402


def own_turn(global_turn: int, player: int, first: int) -> int:
    """全体ターン番号（先手の1ターン目=1）から、そのプレイヤーの自ターン数。"""
    if player == first:
        return (global_turn + 1) // 2
    return global_turn // 2


def play_content(rules, vocab, deck, seed, sides):
    """sides: ("random",) / ("greedy",) / ("policy", model) / ("search",)。"""
    first = seed % 2
    eng = Engine.new_game(rules, [deck, deck], seed, first_player=first)
    import random as _random
    rng = _random.Random(seed * 17 + 1)
    greedy = greedy_policy()
    pols = {}
    for i, side in enumerate(sides):
        if side[0] == "policy":
            pols[i] = model_policy(side[1], vocab,
                                   np.random.default_rng(seed * 31 + i))
        elif side[0] == "random":
            pols[i] = random_policy(rng)
        else:
            pols[i] = greedy
    dets = [LoopDetector(me=0, report_all=True),
            LoopDetector(me=1, report_all=True)]
    loop_at = [None, None]  # ループを最初に検出した自ターン数（プレイヤー別）
    for _ in range(400):
        if eng.s.result is not None:
            break
        me = eng.s.active
        if sides[me][0] == "search":
            ts = TurnSearch(me, 400, opp_policy=greedy)
            eng, _st = ts.run(eng)
            while eng.s.result is None and eng.s.active != me:
                d = eng.advance()
                if d is None:
                    break
                eng.answer(pols[d["player"]](eng, d))
        else:
            cur = me
            while eng.s.result is None and eng.s.active == cur:
                d = eng.advance()
                if d is None:
                    break
                p = d["player"]
                eng.answer(pols[p](eng, d))
                if loop_at[p] is None and dets[p].observe(eng) is not None:
                    loop_at[p] = own_turn(eng.s.turn, p, first)
    res = eng.s.result
    if not res or res.get("winner") is None:
        return None
    w = res["winner"]
    return {
        "winner": w,
        "reason": res.get("reason"),
        "turns": res.get("turn"),
        "winner_own_turns": own_turn(res.get("turn"), w, first),
        "loop_own_turn": loop_at[w],
        "loser_deck": len(eng.s.zones["deck"][1 - w]),
        "loser_shields": len(eng.s.zones["shield"][1 - w]),
    }


def summarize(name, rows):
    rows = [r for r in rows if r]
    n = len(rows)
    if not n:
        print(f"{name}: 有効な対戦なし")
        return
    turns = [r["turns"] for r in rows]
    own = [r["winner_own_turns"] for r in rows]
    reasons = Counter(r["reason"] for r in rows)
    looped = [r for r in rows if r["loop_own_turn"] is not None]
    loop_reasons = Counter(r["reason"] for r in looped)
    fast = sum(1 for o in own if o <= 5)
    print(f"{name}（{n} 局）:")
    print(f"  総ターン数 平均 {sum(turns) / n:.1f}（最小 {min(turns)} / 最大 {max(turns)}）")
    print(f"  勝者の自ターン数 平均 {sum(own) / n:.1f}、5 以内で決着 {fast}/{n}")
    print(f"  終了理由: {dict(reasons)}")
    print(f"  ループ検出された勝ち: {len(looped)}/{n}"
          f"（理由内訳 {dict(loop_reasons)}）")
    if looped:
        lt = [r["loop_own_turn"] for r in looped]
        print(f"  ループ初検出の自ターン 平均 {sum(lt) / len(lt):.1f}"
              f"（最小 {min(lt)} / 最大 {max(lt)}）")


def main() -> int:
    t0 = time.time()
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    prod = Model.load("/home/hatch/workspace/phase14/model_colab_torch.npz")
    dist = Model.load("/home/hatch/workspace/phase18/model_r2.npz")

    configs = [
        ("ランダム vs ランダム（Phase 1 ベンチの条件）",
         [("random",), ("random",)], 20, 0),
        ("貪欲 vs 貪欲", [("greedy",), ("greedy",)], 30, 100),
        ("本番モデル ミラー", [("policy", prod), ("policy", prod)], 30, 200),
        ("蒸留方策 ミラー", [("policy", dist), ("policy", dist)], 30, 300),
        ("探索（P0） vs 貪欲", [("search",), ("greedy",)], 6, 400),
    ]
    for name, sides, games, seed0 in configs:
        rows = [play_content(rules, vocab, deck, seed0 + i, sides)
                for i in range(games)]
        summarize(name, rows)
        print(f"  [{time.time() - t0:.0f}s]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
