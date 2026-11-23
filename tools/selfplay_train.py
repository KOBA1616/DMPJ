"""Phase 4: 自己対戦RLの実行（既定はサガミラーの小規模ラン）。

使い方:
  python tools/selfplay_train.py --iters 10 --games-per-iter 8 --eval-games 20
学習前後で「モデル対ランダム」の勝率を測り、モデルを npz に保存する。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dmsim.ai.encode import Vocab          # noqa: E402
from dmsim.ai.model import Model           # noqa: E402
from dmsim.ai.selfplay import evaluate, train_iters  # noqa: E402
from dmsim.cards.defs import load_rules    # noqa: E402
from tools.bench_2p import load_deck       # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="自己対戦RL（Phase 4）")
    ap.add_argument("--deck", default="data/decks/saga.yaml")
    ap.add_argument("--iters", type=int, default=10)
    ap.add_argument("--games-per-iter", type=int, default=8)
    ap.add_argument("--eval-games", type=int, default=20)
    ap.add_argument("--opponents", default="random,greedy",
                    help="評価相手（カンマ区切り: random / greedy / charge_only）")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--out", default="workspace_ai/model.npz")
    a = ap.parse_args(argv)

    rules = load_rules()
    deck = load_deck(a.deck)
    vocab = Vocab(rules)
    model = Model(len(vocab), seed=a.seed)
    print(f"vocab={len(vocab)} params={sum(v.size for v in model.p.values())}")

    opponents = [s.strip() for s in a.opponents.split(",") if s.strip()]
    t0 = time.perf_counter()
    before, after = {}, {}
    for opp in opponents:
        before[opp] = evaluate(rules, vocab, model, deck, deck, a.eval_games,
                               seed=555, opponent=opp)
        print(f"[eval before] vs {opp}: win rate = {before[opp]['win_rate']:.2f} "
              f"({before[opp]['wins']}W/{before[opp]['losses']}L/{before[opp]['draws']}D)")

    train_iters(rules, vocab, model, deck, deck, a.iters, a.games_per_iter,
                seed=a.seed, lr=a.lr)

    for opp in opponents:
        after[opp] = evaluate(rules, vocab, model, deck, deck, a.eval_games,
                              seed=999, opponent=opp)
        print(f"[eval after]  vs {opp}: win rate = {after[opp]['win_rate']:.2f} "
              f"({after[opp]['wins']}W/{after[opp]['losses']}L/{after[opp]['draws']}D)")
    print(f"total {time.perf_counter() - t0:.1f}s")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(out))
    print(f"saved {out}")
    return {"before": before, "after": after}


if __name__ == "__main__":
    main()
