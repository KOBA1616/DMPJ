#!/usr/bin/env python3
"""探索の蒸留データ生成（Phase 17）。

学習信号を「最終的な勝ち負け」から「探索の結果」に変えるための教師データ。
対戦中の局面で TurnSearch（手作り評価の探索）を実際に回し、
- 探索が選んだ最初の手（方策への正解）
- 探索がたどり着いたターン終了局面の評価（価値への正解、-1..1 に規格化）
を記録する。既存の学習器（REINFORCE＋価値回帰）にそのまま流せる形式。

使い方: python3 tools/distill_collect.py --games 60 --out distill.pkl
"""
from __future__ import annotations

import argparse
import os
import pickle
import random
import sys
import time
from pathlib import Path

os.environ.setdefault("DMSIM_RUST", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim.ai.demo import greedy_policy  # noqa: E402
from dmsim.ai.encode import Vocab, encode_options, encode_state  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.engine.play import random_policy  # noqa: E402
from dmsim.search.leaf_eval import Weights, evaluate  # noqa: E402
from dmsim.search.turn import TurnSearch  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402

W = Weights()


def distill_at(rules, vocab, snap, d, budget: int, greedy):
    """snap（決定 d の直前の局面）で探索を回し、蒸留 item を1つ作る。"""
    st_enc = encode_state(snap, 0, vocab)
    op_enc = encode_options(snap, d, vocab)
    log0 = len(snap.log)
    leaf_eng, _st = TurnSearch(0, budget, opp_policy=greedy).run(snap.clone())
    keys = None
    for a in leaf_eng.log[log0:]:
        if a["p"] == 0:
            keys = a["keys"]
            break
    if not keys:
        return None
    rest = list(keys)
    choice = []
    for i, o in enumerate(d["options"]):
        if o["key"] in rest:
            choice.append(i)
            rest.remove(o["key"])
    if not choice:
        return None
    res = leaf_eng.s.result
    if res is not None and res.get("winner") == 0:
        ret = 1.0
    elif res is not None and res.get("winner") == 1:
        ret = -1.0
    else:
        diff = evaluate(leaf_eng, 0, W) - evaluate(leaf_eng, 1, W)
        ret = max(-1.0, min(1.0, diff / 300.0))
    return {"st": st_enc, "op": op_enc,
            "choice": sorted(choice), "ret": ret}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=60)
    ap.add_argument("--budget", type=int, default=300)
    ap.add_argument("--per-game", type=int, default=5)
    ap.add_argument("--sample-p", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--policy-model", default=None,
                    help="P0 の方策に使うモデル（expert iteration 用）。"
                         "省略時は貪欲方策")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    t0 = time.time()
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    greedy = greedy_policy()
    items: list[dict] = []

    pol0 = greedy
    if args.policy_model:
        import numpy as np

        from dmsim.ai.demo import model_policy
        from dmsim.ai.model import Model
        pm = Model.load(args.policy_model)
        pol0 = model_policy(pm, vocab, np.random.default_rng(args.seed))

    for g in range(args.games):
        rng = random.Random(args.seed + g)
        eng = Engine.new_game(rules, [deck, deck], args.seed + g,
                              first_player=g % 2)
        pols = [pol0, random_policy(rng)]
        made = 0
        for _ in range(4000):
            if eng.s.result is not None:
                break
            snap = eng.clone()
            d = eng.advance()
            if d is None:
                break
            if (d["player"] == 0 and eng.s.active == 0 and made < args.per_game
                    and rng.random() < args.sample_p):
                try:
                    item = distill_at(rules, vocab, snap, d, args.budget,
                                      greedy)
                except Exception:
                    item = None
                if item is not None:
                    items.append(item)
                    made += 1
            eng.answer(pols[d["player"]](eng, d))
        print(f"game {g}: 蒸留 {len(items)} 件（{time.time() - t0:.0f}s）",
              flush=True)

    Path(args.out).write_bytes(pickle.dumps(items))
    print(f"保存: {args.out}（{len(items)} 件、{time.time() - t0:.0f}s）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
