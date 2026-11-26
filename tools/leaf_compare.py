#!/usr/bin/env python3
"""葉評価の比較（Phase 12）: 手作り評価 vs 学習した価値ヘッド vs 混合。

2つの物差しで比べる。
1. 予測の正確さ: 対戦の途中局面を集め、各評価が最終勝敗とどれだけ
   一致するか（勝った側を高く評価した割合＝AUC相当の一致率）。
2. 探索での実力: TurnSearch の value_fn を差し替えて、サガループ局面で
   勝ち筋発見までに使うノード数と発見可否を比べる。

使い方: python3 tools/leaf_compare.py --model model.npz --games 40
（--model が無ければ小さく学習してから比べる）
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import time
from pathlib import Path

os.environ.setdefault("DMSIM_RUST", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import yaml  # noqa: E402

from dmsim.ai.encode import Vocab, encode_state  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import train_iters  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.engine.play import random_policy  # noqa: E402
from dmsim.search.leaf_eval import Weights, evaluate  # noqa: E402
from dmsim.search.turn import TurnSearch  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402

W = Weights()


def collect_positions(rules, deck_a, deck_b, games: int, seed: int):
    """ランダム対戦の途中局面（エンジンの複製）と最終勝者を集める。"""
    rng = random.Random(seed)
    out = []
    for g in range(games):
        first = g % 2
        eng = Engine.new_game(rules, deck_a, deck_b, rng, first_player=first)
        snaps = []
        for step in range(400):
            d = eng.advance()
            if d is None:
                break
            if step % 7 == 3:      # 間引いて局面を保存
                snaps.append(eng.clone())
            eng.answer(random_policy(rng)(eng, d))
        res = eng.s.result
        if res and res.get("winner") in (0, 1):
            out += [(s, res["winner"]) for s in snaps]
    return out


def agreement(positions, score_fn) -> float:
    """勝った側から見た評価が正の向きだった割合（0.5=無情報, 1.0=完璧）。"""
    ok = tot = 0
    for eng, winner in positions:
        v = score_fn(eng, winner)
        tot += 1
        ok += 1 if v > 0 else (0.5 if v == 0 else 0)
    return ok / max(tot, 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--deck", default="data/decks/saga.yaml")
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    t0 = time.time()
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck(args.deck)
    if args.model and Path(args.model).exists():
        model = Model.load(args.model)
        print(f"モデル: {args.model} を読み込み")
    else:
        model = Model(len(vocab), seed=args.seed)
        print("モデル: 小規模に学習してから比較します（30 iter × 8局）")
        train_iters(rules, vocab, model, deck, deck, 30, 8,
                    seed=args.seed, log=lambda h: None)

    positions = collect_positions(rules, deck, deck, args.games, args.seed + 5)
    print(f"局面コーパス: {len(positions)} 局面（{args.games} 局）")

    def s_leaf(eng, me):
        return evaluate(eng, me, W) - evaluate(eng, 1 - me, W)

    def s_value(eng, me):
        return float(model.value(encode_state(eng, me, vocab)))

    def s_blend(eng, me):
        # 桁を揃える: leaf は数百点スケール、価値は -1..1
        return s_value(eng, me) * 300.0 + s_leaf(eng, me)

    for name, fn in [("手作り評価", s_leaf), ("価値ヘッド", s_value),
                     ("混合", s_blend)]:
        print(f"予測一致率 {name}: {agreement(positions, fn):.3f}")

    # 探索での実力: サガループ局面で勝ち筋を探す
    spec = yaml.safe_load(
        Path("tests/saga_loop_first_setup.yaml").read_text(encoding="utf-8"))
    for name, vfn in [("手作り評価", None),
                      ("価値ヘッド", lambda e, me: float(
                          model.value(encode_state(e, me, vocab))) * 300.0),
                      ("混合", lambda e, me: float(
                          model.value(encode_state(e, me, vocab))) * 300.0
                       + evaluate(e, me, W))]:
        eng = sc.build(rules, spec)
        ts = TurnSearch(0, 1500, value_fn=vfn)
        leaf, st = ts.run(eng)
        r = leaf.s.result
        won = r is not None and r.get("winner") == 0
        print(f"探索（{name}）: 勝ち筋 {'発見' if won else '未発見'}"
              f" / ノード {st.nodes}")
    print(f"合計 {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
