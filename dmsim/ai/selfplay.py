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


def model_policy(model: Model, vocab: Vocab, rng, greedy: bool = False,
                 aggregate: bool = False, privileged: bool = False):
    def pol(eng, d):
        st = encode_state(eng, d["player"], vocab, privileged=privileged)
        op = encode_options(eng, d, vocab)
        choice, _, _ = model.act(st, op, rng, greedy=greedy,
                                 aggregate=aggregate)
        return sorted(choice)
    return pol


def collect_games(rules, vocab: Vocab, model: Model, deck_a, deck_b,
                  games: int, seed: int = 0, greedy: bool = False,
                  aggregate: bool = False, privileged: bool = False):
    """自己対戦で軌跡を集める。戻り: (batch, 勝者リスト)。batch の各要素は学習用 dict。

    aggregate=True で等価手の集約（Phase 26-1、単一選択のみ）を有効にする。
    軌跡の choice はグループ代表の番号になり、学習側も同じ aggregate 指定で
    グループ確率の logp を使うこと。
    privileged=True で軌跡の局面に特権情報（相手の手札）を含める
    （Phase 26-3。価値ヘッドの学習専用で、方策の選択には影響しない）。"""
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
            st = encode_state(e, d["player"], vocab, privileged=privileged)
            op = encode_options(e, d, vocab)
            choice, _, _ = model.act(st, op, rng, greedy=greedy,
                                     aggregate=aggregate)
            _traj.append((st, op, sorted(choice), d["player"]))
            return sorted(choice)

        result = run(eng, [pol, pol])
        w = result["winner"] if result else None
        winners.append(w)
        for st, op, choice, player in traj:
            ret = 0.0 if w is None else (1.0 if w == player else -1.0)
            batch.append({"st": st, "op": op, "choice": choice, "ret": ret})
    return batch, winners


def opponent_policy(name: str, seed: int):
    """評価相手の方策。random（無作為）/ greedy（leaf_eval の重みで貪欲）/ charge_only。"""
    import random as _random
    if name == "random":
        return random_policy(_random.Random(seed))
    if name == "greedy":
        from ..search.turn import greedy_policy
        return greedy_policy()
    if name == "charge_only":
        from ..search.turn import charge_only_policy
        return charge_only_policy
    raise ValueError(f"unknown opponent {name}")


def collect_games_parallel(rules, vocab: Vocab, model: Model, deck_a, deck_b,
                           games: int, seed: int = 0, workers: int = 2,
                           aggregate: bool = False):
    """collect_games のマルチプロセス版。fork で rules/vocab を引き継ぎ、
    モデルのパラメータだけを各ワーカーへ渡す。結果（batch, winners）は直列版と同形。"""
    import multiprocessing as mp

    per = [games // workers + (1 if i < games % workers else 0) for i in range(workers)]
    jobs = []
    done = 0
    for i, n in enumerate(per):
        if n:
            jobs.append((None, None, dict(model.p), deck_a, deck_b, n,
                         seed + i * 1000, aggregate))
            done += n
    ctx = mp.get_context("fork")
    # fork した子ではモジュールグローバル経由で rules/vocab を渡す（pickle を避ける）
    global _PAR_RULES, _PAR_VOCAB
    _PAR_RULES, _PAR_VOCAB = rules, vocab
    try:
        with ctx.Pool(workers) as pool:
            results = pool.map(_collect_chunk_global, jobs)
    finally:
        _PAR_RULES = _PAR_VOCAB = None
    batch, winners = [], []
    for b, w in results:
        batch.extend(b)
        winners.extend(w)
    return batch, winners


_PAR_RULES = None
_PAR_VOCAB = None


def _collect_chunk_global(job):
    _, _, params, deck_a, deck_b, games, seed = job[:7]
    aggregate = job[7] if len(job) > 7 else False
    if "attn_q" in params:
        from .model_attn import AttnModel
        model = AttnModel(len(_PAR_VOCAB))
    else:
        model = Model(len(_PAR_VOCAB))
    for k, v in params.items():
        model.p[k] = v
    return collect_games(_PAR_RULES, _PAR_VOCAB, model, deck_a, deck_b, games,
                         seed=seed, aggregate=aggregate)


def evaluate(rules, vocab: Vocab, model: Model, deck_a, deck_b,
             games: int, seed: int = 1000, opponent: str = "random",
             aggregate: bool = False) -> dict:
    """モデル（greedy 選択）対 指定方策の勝率。両座席を半分ずつ。"""
    wins = losses = draws = 0
    for g in range(games):
        first = g % 2
        model_seat = g % 2  # 半分の局でモデルが先攻側/後攻側の両方を担う
        eng = Engine.new_game(rules, [deck_a, deck_b], seed * 100003 + g, first)
        eng = rustcore.maybe_rust(eng)
        mp = model_policy(model, vocab, np.random.default_rng(seed + g),
                          greedy=True, aggregate=aggregate)
        rp = opponent_policy(opponent, seed * 7 + g)
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
            "win_rate": wins / n if n else 0.0, "opponent": opponent}


def collect_games_rust(rules, vocab: Vocab, model: Model, deck_a, deck_b,
                       games: int, seed: int = 0):
    """Phase 7: 方策を Rust に埋め込んだ一括収集（dmcore.run_batch_model）。
    軌跡の特徴は Rust 側エンコード（Python 版とパリティ検証済み）。
    戻りは collect_games と同じ (batch, winners)。"""
    from dmsim.engine import rustcore
    states = [rustcore.new_game(rules, [deck_a, deck_b], seed + g, g % 2)
              for g in range(games)]
    results = rustcore.run_batch_model(rules, states, model, vocab.ids, seed=seed)
    batch, winners = [], []
    for r in results:
        if "error" in r:
            raise RuntimeError(f"run_batch_model: {r['error']}")
        winners.append(r["winner"])
        for t in r["traj"]:
            batch.append({
                "st": t["st"], "op": t["op"], "choice": t["choice"],
                "ret": 1.0 if r["winner"] == t["player"] else -1.0,
            })
    return batch, winners


def train_iters(rules, vocab: Vocab, model: Model, deck_a, deck_b,
                iters: int, games_per_iter: int, seed: int = 0,
                lr: float = 3e-3, log=print, workers: int = 1,
                collect: str = "python", demo: list | None = None,
                demo_repeat: int = 1, aggregate: bool = False) -> list[dict]:
    if aggregate and collect == "rust":
        # Rust 埋め込み収集の軌跡には grp が無く集約できない（Phase 26-1 対象外）
        raise ValueError("等価手の集約は rust 収集経路では未対応です"
                         "（python 収集を使ってください）")
    hist = []
    for it in range(iters):
        if collect == "rust":
            batch, winners = collect_games_rust(
                rules, vocab, model, deck_a, deck_b, games_per_iter,
                seed=seed + it)
        elif workers > 1:
            batch, winners = collect_games_parallel(
                rules, vocab, model, deck_a, deck_b, games_per_iter,
                seed=seed + it, workers=workers, aggregate=aggregate)
        else:
            batch, winners = collect_games(rules, vocab, model, deck_a, deck_b,
                                           games_per_iter, seed=seed + it,
                                           aggregate=aggregate)
        if demo:   # 発見の還元（Phase 11）: 探索の教材を毎 iter 混ぜる
            batch = batch + demo * demo_repeat
        loss, grads = model.loss_and_grads(batch, aggregate=aggregate)
        model.step(grads, lr=lr)
        wr = np.mean([1.0 if w == 0 else 0.0 for w in winners]) if winners else 0.0
        hist.append({"iter": it, "loss": float(loss), "decisions": len(batch),
                     "p0_win_rate": float(wr)})
        log(f"iter {it}: loss={loss:.3f} decisions={len(batch)} "
            f"selfplay P0 win rate={wr:.2f}")
    return hist
