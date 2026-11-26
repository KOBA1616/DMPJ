#!/usr/bin/env python3
"""Phase 23 の最終評価: 土台モデルとカリキュラム学習モデルを同一条件で比較。

指標: ミラーのループキル率、対貪欲勝率、段階別（A/B/C）の勝率と
ループキル率、そして「芽消しチャージ率」—手札にも墓地にも残りが無い
中核カードをマナに埋める割合（序盤4回までのチャージで測定）。
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import evaluate, model_policy  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.curriculum_train import eval_positions  # noqa: E402
from tools.game_content import play_content  # noqa: E402

CORE = {"dm22ex2-021", "dmrp03-036", "dmex10-020", "dm22ex1-007"}
MODELS = {
    "土台(11,200局)": "/home/hatch/workspace/phase21/model_colab_big.npz",
    "カリキュラム後": (sys.argv[1] if len(sys.argv) > 1 else
                    "/home/hatch/workspace/phase23/model_curriculum.npz"),
}


def stranding_probe(rules, vocab, model, deck, games: int = 20):
    """序盤のチャージで「芽消し」（残りの無い中核を埋める）をした割合。"""
    strand = core_charges = charges = 0
    for g in range(games):
        first = g % 2
        eng = Engine.new_game(rules, [deck, deck], 12000 + g,
                              first_player=first)
        pols = {0: model_policy(model, vocab, np.random.default_rng(900 + 2 * g)),
                1: model_policy(model, vocab, np.random.default_rng(901 + 2 * g))}
        seen = Counter()
        for _ in range(600):
            if eng.s.result is not None:
                break
            d = eng.advance()
            if d is None:
                break
            p = d["player"]
            ans = pols[p](eng, d)
            if d.get("kind") == "charge":
                seen[p] += 1
                if seen[p] <= 4 and ans:
                    opts = [o["key"].split(":", 1)[1] for o in d["options"]
                            if o["key"].startswith("charge:")]
                    cid = d["options"][ans[0]]["key"].split(":", 1)[1]
                    charges += 1
                    if cid in CORE:
                        core_charges += 1
                        in_hand = opts.count(cid) - 1
                        in_grave = sum(
                            1 for c in eng.s.zones["graveyard"][p]
                            if eng.s.cards[c].defn == cid)
                        if in_hand == 0 and in_grave == 0:
                            strand += 1
            eng.answer(ans)
    return strand, core_charges, charges


def main() -> int:
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    for name, path in MODELS.items():
        m = Model.load(path)
        rows = [play_content(rules, vocab, deck, 40000 + i,
                             (("policy", m), ("policy", m)))
                for i in range(30)]
        rows = [r for r in rows if r]
        kills = sum(1 for r in rows if r["loop_own_turn"] is not None)
        turns = sum(r["turns"] for r in rows) / len(rows)
        print(f"[{name}] ミラー30局: ループキル {kills}/30、"
              f"総ターン {turns:.1f}", flush=True)
        r = evaluate(rules, vocab, m, deck, deck, 40, seed=999,
                     opponent="greedy")
        print(f"[{name}] 対貪欲40局: {r['win_rate']:.2f}", flush=True)
        ev = eval_positions(rules, vocab, m)
        line = " / ".join(
            f"{s}: 勝率 {ev[s][0]:.2f} ループキル {ev[s][1]:.2f}"
            for s in "ABC")
        print(f"[{name}] 段階別: {line}", flush=True)
        st, cc, ch = stranding_probe(rules, vocab, m, deck)
        print(f"[{name}] 芽消しチャージ: {st}/{ch}"
              f"（中核チャージ自体は {cc} 件）", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
