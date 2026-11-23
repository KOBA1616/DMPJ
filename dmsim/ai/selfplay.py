"""自己対戦の収集・学習・評価（Phase 4）。

収集は駆動方式（Python Engine を maybe_rust で包む）で1局ずつ回し、各決定の
（局面エンコード、選択肢エンコード、選んだ選択、決定プレイヤー）を記録する。
終局後に勝敗を付け、REINFORCE（価値ベースライン）で更新する。
対局中探索は使わない（ポケカABC上位の結論どおり、単発推論のみ）。
"""
from __future__ import annotations

import numpy as np

from ..engine.core import Engine
from ..engine.play import random_policy, run
from ..engine import rustcore
from .encode import Vocab, encode_options, encode_state
from .model import Model


def model_policy(model: Model, vocab: Vocab, rng, greedy: bool = False):
    def pol(eng, d):
        st = encode_state(eng, d["player"], vocab)
        op = encode_options(eng, d, vocab)
        choice, _, _ = model.act(st, op, rng, greedy=greedy)
        return sorted(choice)
    return pol


def collect_games(rules, vocab: Vocab, model: Model, deck_a, deck_b,
                  games: int, seed: int = 0, greedy: bool = False):
    """自己対戦で軌跡を集める。戻り: (batch, 勝者リスト)。batch の各要素は学習用 dict。"""
    rng = np.random.default_rng(seed)
    py_rng = __import__("random").Random(seed)
    batch: list[dict] = []
    winners: list[int] = []
    for g in range(games):
        first = g % 2
        eng = Engine.new_game(rules, [deck_a, deck_b], seed * 100003 + g, first)
        eng = rustcore.maybe_rust(eng)
        traj: list[tuple[dict, dict, list[int], int]] = []

        def pol(e, d, _traj=traj):
            st = encode_state(e, d["player"], vocab)
            op = encode_options(e, d, vocab)
            choice, _, _ = model.act(st, op, rng, greedy=greedy)
            _traj.append((st, op, sorted(choice), d["player"]))
            return sorted(choice)

        result = run(eng, [pol, pol])
        w = result["winner"] if result else None
        winners.append(w)
        for st, op, choice, player in traj:
            ret = 0.0 if w is None else (1.0 if w == player else -1.0)
            batch.append({"st": st, "op": op, "choice": choice, "ret": ret})
    return batch, winners


def evaluate(rules, vocab: Vocab, model: Model, deck_a, deck_b,
             games: int, seed: int = 1000) -> dict:
    """モデル（greedy）対ランダム方策の勝率。両座席を半分ずつ。"""
    import random as _random
    wins = losses = draws = 0
    for g in range(games):
        first = g % 2
        model_seat = g % 2  # 半分の局でモデルが先攻側/後攻側の両方を担う
        eng = Engine.new_game(rules, [deck_a, deck_b], seed * 100003 + g, first)
        eng = rustcore.maybe_rust(eng)
        mp = model_policy(model, vocab, np.random.default_rng(seed + g), greedy=True)
        rp = random_policy(_random.Random(seed * 7 + g))
        pols = [mp, rp] if model_seat == 0 else [rp, mp]
        result = run(eng, pols)
        w = result["winner"] if result else None
        if w is None:
            draws += 1
        elif w == model_seat:
            wins += 1
        else:
            losses += 1
    n = wins + losses
    return {"games": games, "wins": wins, "losses": losses, "draws": draws,
            "win_rate": wins / n if n else 0.0}


def train_iters(rules, vocab: Vocab, model: Model, deck_a, deck_b,
                iters: int, games_per_iter: int, seed: int = 0,
                lr: float = 3e-3, log=print) -> list[dict]:
    hist = []
    for it in range(iters):
        batch, winners = collect_games(rules, vocab, model, deck_a, deck_b,
                                       games_per_iter, seed=seed + it)
        loss, grads = model.loss_and_grads(batch)
        model.step(grads, lr=lr)
        wr = np.mean([1.0 if w == 0 else 0.0 for w in winners]) if winners else 0.0
        hist.append({"iter": it, "loss": float(loss), "decisions": len(batch),
                     "p0_win_rate": float(wr)})
        log(f"iter {it}: loss={loss:.3f} decisions={len(batch)} "
            f"selfplay P0 win rate={wr:.2f}")
    return hist
