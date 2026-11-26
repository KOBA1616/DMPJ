#!/usr/bin/env python3
"""Phase 26-4: カード表現の A/B 学習（ID 埋め込み vs 属性射影）。

公平な比較のため、両モデルともゼロから同一条件で学習する:
- レシピは 26-2/26-3 のリーグ学習（相手プール混合 mirror 0.45 /
  snapshot 0.20 / greedy 0.15 / search 0.10 / charge 0.10、集約 ON、
  特権価値＋トラッカー有効、lr 3e-3、seed 26、100 iter × 20局
  = 2,000局）。対局は tools.priv_train.play_priv_game をそのまま使う。
- 違うのはカード表現だけ（--repr id: Model の ID 埋め込み、
  --repr attr: AttrModel の属性射影）。共有パラメータの初期値は
  同じ seed から同じ値になる（AttrModel は埋め込み分岐だけを
  別乱数で初期化する）。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from dmsim.ai.attributes import build_attribute_matrix  # noqa: E402
from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.model_attr import AttrModel  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.league_train import KINDS, parse_mix  # noqa: E402
from tools.priv_train import play_priv_game  # noqa: E402

OUT = Path("/home/hatch/workspace/phase26attr")
MIX = "mirror=0.45,snapshot=0.20,greedy=0.15,search=0.10,charge=0.10"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repr", choices=["id", "attr"], required=True)
    ap.add_argument("--iters", type=int, default=100)
    ap.add_argument("--games-per-iter", type=int, default=20)
    ap.add_argument("--mix", default=MIX)
    ap.add_argument("--snapshot-every", type=int, default=10)
    ap.add_argument("--pool-max", type=int, default=5)
    ap.add_argument("--search-budget", type=int, default=300)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--seed", type=int, default=26)
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    out = a.out or str(OUT / f"model_{a.repr}.npz")
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")

    attr = attr_names = None
    if a.repr == "attr":
        attr, attr_names = build_attribute_matrix(rules, vocab)

    def fresh():
        if a.repr == "attr":
            m = AttrModel(attr, seed=a.seed)
            m.attr_names = attr_names
            return m
        return Model(len(vocab), seed=a.seed)

    def from_params(params):
        m = fresh()
        for k, v in params.items():
            m.p[k] = v
        return m

    model = fresh()
    mix = parse_mix(a.mix)
    probs = np.array([mix[k] for k in KINDS])
    rng = np.random.default_rng(a.seed)
    pool: list[tuple[str, dict]] = [
        ("init", {k: v.copy() for k, v in model.p.items()})]
    pool_models: dict[str, Model] = {}
    total = {k: 0 for k in KINDS}
    total_wins = {k: 0 for k in KINDS}
    print(f"repr={a.repr} mix={mix} iters={a.iters} "
          f"games/iter={a.games_per_iter} seed={a.seed} ゼロから学習",
          flush=True)
    t0 = time.time()
    gc = 0
    for it in range(a.iters):
        counts = rng.multinomial(a.games_per_iter, probs)
        plan = [k for k, c in zip(KINDS, counts) for _ in range(c)]
        rng.shuffle(plan)
        batch: list[dict] = []
        iter_wins = {k: 0 for k in KINDS}
        for kind in plan:
            learner_seat = gc % 2
            first = (gc // 2) % 2
            opp_model = None
            if kind == "snapshot":
                name, params = pool[int(rng.integers(0, len(pool)))]
                if name not in pool_models:
                    pool_models[name] = from_params(params)
                opp_model = pool_models[name]
            b, w = play_priv_game(
                rules, vocab, model, deck, kind, opp_model,
                seed=1000003 * a.seed + gc, first=first,
                learner_seat=learner_seat,
                search_budget=a.search_budget)
            batch.extend(b)
            total[kind] += 1
            if w == learner_seat:
                iter_wins[kind] += 1
                total_wins[kind] += 1
            gc += 1
        loss, grads = model.loss_and_grads(batch, aggregate=True)
        model.step(grads, lr=a.lr)
        cnt_s = " ".join(f"{k}:{counts[i]}" for i, k in enumerate(KINDS)
                         if counts[i])
        win_s = " ".join(
            f"{k} {iter_wins[k]}/{counts[i]}"
            for i, k in enumerate(KINDS) if counts[i])
        print(f"iter {it}: loss={loss:.3f} dec={len(batch)} [{cnt_s}] "
              f"勝ち [{win_s}] ({time.time() - t0:.0f}s)", flush=True)
        if (it + 1) % a.snapshot_every == 0 or it == a.iters - 1:
            name = f"iter{it + 1}"
            pool.append((name, {k: v.copy() for k, v in model.p.items()}))
            while len(pool) > a.pool_max:
                old, _ = pool.pop(0)
                pool_models.pop(old, None)
            model.save(out)
            print(f"  snapshot -> {out} pool={[n for n, _ in pool]}",
                  flush=True)
    print(f"完了: {gc} 局（{time.time() - t0:.0f}s） -> {out}", flush=True)
    for k in KINDS:
        if total[k]:
            print(f"  相手 {k}: {total[k]} 局、学習者の勝率 "
                  f"{total_wins[k] / total[k]:.2f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
