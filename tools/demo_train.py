#!/usr/bin/env python3
"""発見の還元（Phase 11）の検証ツール。

探索が見つけたコンボ（既定はサガループの局面）を教材化し、
「コンボ実行率」が教材学習の前後でどう変わるかを測る。
ついでに通常対戦（対ランダム）の勝率も測り、教材で壊れていないかを見る。

使い方: python3 tools/demo_train.py --iters 30 --trials 16
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import time
from pathlib import Path

os.environ.setdefault("DMSIM_RUST", "0")   # 状態を読む方策は Python 駆動が速い

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import yaml  # noqa: E402

from dmsim.ai.demo import execution_rate, record_demo  # noqa: E402
from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import evaluate, train_iters  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from dmsim.search import loop_first as lf  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", default="tests/saga_loop_first_setup.yaml")
    ap.add_argument("--deck", default="data/decks/saga.yaml")
    ap.add_argument("--iters", type=int, default=30)
    ap.add_argument("--games-per-iter", type=int, default=8)
    ap.add_argument("--trials", type=int, default=16)
    ap.add_argument("--eval-games", type=int, default=20)
    ap.add_argument("--budget", type=int, default=800)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="")
    ap.add_argument("--demo-cache", default="",
                    help="教材を pickle で保存/再利用するパス（生成が高価なため）")
    ap.add_argument("--no-demo", action="store_true",
                    help="教材なしで学習する（対照実験用）")
    args = ap.parse_args()

    t0 = time.time()
    rules = load_rules()
    vocab = Vocab(rules)
    spec = yaml.safe_load(Path(args.setup).read_text(encoding="utf-8"))
    eng = sc.build(rules, spec)
    # 教材にループ区間を含めるため、探索が自分でループを回して勝つ経路を切る
    import dmsim.search.turn as _T
    _T.REPEAT_FIRST = False
    found = lf.two_stage(eng, 0, discover_budget=1500, seek_budget=1500,
                         first_win_only=False)
    winners = [f for f in found if f.wins]
    if not winners:
        print("探索で勝ち筋が見つからないため中断")
        return 1
    # 教材としてはループを最も回す勝ち筋が一番濃い
    f = max(winners, key=lambda g: max(w["cycles"] for w in g.wins))
    cycles = max(w["cycles"] for w in f.wins)
    print(f"発見: ループ delta={f.cert.delta} / 勝ち cycles={cycles} "
          f"reason={f.wins[0]['reason']}（{time.time() - t0:.0f}s）")

    if args.demo_cache and Path(args.demo_cache).exists():
        import pickle
        demo = pickle.loads(Path(args.demo_cache).read_bytes())
        print(f"教材: キャッシュから {len(demo)} 決定")
    else:
        demo = record_demo(rules, vocab, f, cycles, budget=args.budget)
        print(f"教材: {len(demo)} 決定（{time.time() - t0:.0f}s）")
        if args.demo_cache:
            import pickle
            Path(args.demo_cache).write_bytes(pickle.dumps(demo))

    from tools.bench_2p import load_deck
    deck = load_deck(args.deck)
    model = Model(len(vocab), seed=args.seed)
    base_exec = execution_rate(rules, vocab, model, f.start,
                               trials=args.trials, seed=1000)
    base_rand = evaluate(rules, vocab, model, deck, deck,
                         args.eval_games, seed=1000,
                         opponent="random")["win_rate"]
    print(f"学習前: コンボ実行率 {base_exec:.2f} / 対ランダム {base_rand:.2f}")

    train_iters(rules, vocab, model, deck, deck, args.iters,
                args.games_per_iter, seed=args.seed,
                demo=None if args.no_demo else demo,
                log=lambda h: None)
    post_exec = execution_rate(rules, vocab, model, f.start,
                               trials=args.trials, seed=1000)
    post_greedy = execution_rate(rules, vocab, model, f.start,
                                 trials=1, greedy=True)
    post_rand = evaluate(rules, vocab, model, deck, deck,
                         args.eval_games, seed=2000,
                         opponent="random")["win_rate"]
    print(f"学習後: コンボ実行率 {post_exec:.2f}（greedy {post_greedy:.0f}）"
          f" / 対ランダム {post_rand:.2f}")
    print(f"合計 {time.time() - t0:.0f}s")
    if args.out:
        model.save(args.out)
        print(f"saved {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
