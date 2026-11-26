#!/usr/bin/env python3
"""Phase 26-2: 相手プール（方策リーグ）学習。

自己対戦がサガミラー単一分布に飽和している（Phase 22 の量の逓減、
Phase 24 の到達率低下）ことへの対策として、相手をゲームごとに
プールから抽選する:

  mirror   現行の自分（ミラー）
  snapshot 過去の自分のスナップショット（プールから1つ抽選）
  greedy   貪欲方策（leaf_eval の重み）
  search   探索プレイヤー（TurnSearch、予算は引数。Phase 24 (c) の一般化）
  charge   チャージのみ

学習者の座席はゲームごとに交代し、軌跡は学習者の決定だけから取る
（Phase 24 の milestone_train.py の探索相手混合と同じ流儀）。
集約（Phase 26-1）は ON を既定とする。
"""
from __future__ import annotations

import argparse
import copy
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from dmsim.ai.encode import Vocab, encode_options, encode_state  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.search.turn import TurnSearch, charge_only_policy, greedy_policy  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402

OUT = Path("/home/hatch/workspace/phase26")
BASE = "/home/hatch/workspace/phase21/model_colab_big.npz"
KINDS = ("mirror", "snapshot", "greedy", "search", "charge")
DEFAULT_MIX = "mirror=0.40,snapshot=0.20,greedy=0.15,search=0.15,charge=0.10"


def parse_mix(s: str) -> dict[str, float]:
    mix = {k: 0.0 for k in KINDS}
    for part in s.split(","):
        k, v = part.split("=")
        k = k.strip()
        if k not in mix:
            raise ValueError(f"unknown opponent kind {k}")
        mix[k] = float(v)
    tot = sum(mix.values())
    if tot <= 0:
        raise ValueError("mix の合計が 0 です")
    return {k: v / tot for k, v in mix.items()}


def play_league_game(rules, vocab, model, deck, opp_kind: str,
                     opp_model: Model | None, seed: int, first: int,
                     learner_seat: int, search_budget: int = 300,
                     learner_greedy: bool = False, collect: bool = True):
    """学習者 vs プール相手の1局。戻り: (batch要素リスト, 勝者)。

    軌跡は学習者の決定だけ。search 相手は自分のターンを TurnSearch で
    丸ごと指し、学習者ターン中の相手決定は貪欲で代行する
    （Phase 24 (c) の play_recorded と同じ扱い）。
    """
    eng = Engine.new_game(rules, [deck, deck], seed, first)
    rng = np.random.default_rng(seed * 7919 + learner_seat + 1)
    greedy = greedy_policy()
    opp_seat = 1 - learner_seat
    traj: list[tuple[dict, dict, list[int]]] = []
    for _ in range(1000):
        if eng.s.result is not None:
            break
        if opp_kind == "search" and eng.s.active == opp_seat:
            ts = TurnSearch(opp_seat, search_budget, opp_policy=greedy)
            eng, _st = ts.run(eng)
            continue
        d = eng.advance()
        if d is None:
            break
        p = d["player"]
        if p == learner_seat:
            st = encode_state(eng, p, vocab)
            op = encode_options(eng, d, vocab)
            choice, _, _ = model.act(st, op, rng, greedy=learner_greedy,
                                     aggregate=True)
            if collect:
                traj.append((st, op, sorted(choice)))
            eng.answer(sorted(choice))
        elif opp_kind in ("mirror", "snapshot"):
            om = model if opp_kind == "mirror" else opp_model
            st = encode_state(eng, p, vocab)
            op = encode_options(eng, d, vocab)
            choice, _, _ = om.act(st, op, rng, aggregate=True)
            eng.answer(sorted(choice))
        elif opp_kind == "greedy":
            eng.answer(greedy(eng, d))
        elif opp_kind == "charge":
            eng.answer(charge_only_policy(eng, d))
        else:  # search: 学習者ターン中の相手決定は貪欲で代行
            eng.answer(greedy(eng, d))
    res = eng.s.result
    w = res.get("winner") if res else None
    ret = 0.0 if w is None else (1.0 if w == learner_seat else -1.0)
    batch = [{"st": st, "op": op, "choice": ch, "ret": ret}
             for st, op, ch in traj]
    return batch, w


def make_model(vocab: Vocab, params: dict) -> Model:
    m = Model(len(vocab))
    for k, v in params.items():
        m.p[k] = v
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=100)
    ap.add_argument("--games-per-iter", type=int, default=20)
    ap.add_argument("--mix", default=DEFAULT_MIX)
    ap.add_argument("--snapshot-every", type=int, default=10)
    ap.add_argument("--pool-max", type=int, default=5)
    ap.add_argument("--search-budget", type=int, default=300)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--seed", type=int, default=26)
    ap.add_argument("--init", default=BASE)
    ap.add_argument("--out", default=str(OUT / "model_league.npz"))
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    snap_dir = OUT / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    model = Model.load(a.init)
    mix = parse_mix(a.mix)
    probs = np.array([mix[k] for k in KINDS])
    rng = np.random.default_rng(a.seed)

    # スナップショットプール: (名前, パラメータ)。初期値は土台モデル。
    pool: list[tuple[str, dict]] = [
        ("base", {k: v.copy() for k, v in model.p.items()})]
    pool_models: dict[str, Model] = {}
    total = {k: 0 for k in KINDS}
    total_wins = {k: 0 for k in KINDS}
    print(f"init={a.init} mix={mix} iters={a.iters} "
          f"games/iter={a.games_per_iter}", flush=True)
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
                    pool_models[name] = make_model(vocab, params)
                opp_model = pool_models[name]
            b, w = play_league_game(
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
            snap_path = snap_dir / f"league_{name}.npz"
            model.save(str(snap_path))
            pool.append((name, {k: v.copy() for k, v in model.p.items()}))
            while len(pool) > a.pool_max:
                old, _ = pool.pop(0)
                pool_models.pop(old, None)
            model.save(a.out)
            print(f"  snapshot {snap_path} pool={[n for n, _ in pool]}",
                  flush=True)
    print(f"完了: {gc} 局（{time.time() - t0:.0f}s）", flush=True)
    for k in KINDS:
        if total[k]:
            print(f"  相手 {k}: {total[k]} 局、学習者の勝率 "
                  f"{total_wins[k] / total[k]:.2f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
