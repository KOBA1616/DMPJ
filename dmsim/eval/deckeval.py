"""デッキ案の採否評価（P1-S6 で deckplan/evaluate.py から評価 eval/ へ下ろした。依存は S4 以下のみ）。

採否と評価の接続。測るのは dmsim.eval のハーネス、採否は固定の AcceptRule だけ。

指標と規則は自動で変えない（AcceptRule は凍結した版つき値。変更は人が新しい版を追加する）。
採否の根拠は FAIR 水準の値のみ（CHEAT は上限値として併記するだけ）。"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..eval.stats import paired_diff
from ..base import store


@dataclass(frozen=True)
class AcceptRule:
    version: str = "v0"
    turn: int = 4                    # 指標: この手番までのキル率
    level: str = "fair"
    alpha: float = 0.05


# scorer: (デッキ名->ID列, 評価セット) -> {(seed, 先後): キルターン|None}。ハーネス接続は harness_scorer。
Scorer = Callable[[list[str]], "dict[tuple, int | None]"]


_JOB: dict = {}


def _run_chunk(i: int) -> dict:
    return _JOB["fn"](_JOB["deck"], _JOB["chunks"][i])


def spec_with_deck(setup: dict, deck: list[str]) -> dict:
    """仕込み済み開始局面（手札・マナ・墓地は固定）の山札を、候補デッキの残り札に差し替える。
    デッキの変更（部品・準備札の追加）が山札経由でだけ効くので、局面を固定したまま候補どうしを比べられる。"""
    from collections import Counter
    left = Counter(deck)
    p0 = setup.get("p0", {})
    for z in ("hand", "mana", "graveyard", "battle"):
        for c in p0.get(z, []):
            if left.get(c, 0) > 0:
                left[c] -= 1
    rest = sorted(left.elements())
    return {**setup, "p0": {**p0, "deck": rest}, "deck_size": len(rest), "shuffle_deck": True}


def stage_value(kill, board, cards, turn: int) -> float:
    """4ターン時点の段階進捗（連続値の副指標）: 必要カード揃い→盤面→キルの各段階に、到達していれば 0〜1（早いほど大きい）を足す。
    最終採用には使わない（採否は kill 率の有意差のみ）。粗比較のふるい用。"""
    v = 0.0
    for t in (cards, board, kill):
        if t is not None and t <= turn:
            v += min(1.0, (turn + 1 - t) / turn)
    return v


def harness_scorer(rules, opp_deck: list[str], seeds: list[int], rule: AcceptRule = AcceptRule(), setup: dict | None = None, workers: int = 1,
                   stage_spec=None, **cfg_kw) -> Scorer:
    """stage_spec（eval.progress.ProgressSpec）を渡すと、値が (キルターン, 段階進捗) の組になる（粗比較用）。"""
    from ..eval.api import Candidate, EvalSettings, run_eval
    from ..eval.harness import cell_key
    from ..play_api import InfoLevel

    def one(deck: list[str], sd: list[int]) -> dict:
        cand = Candidate(deck=tuple(deck), start_spec=spec_with_deck(setup, deck) if setup else None)
        st = EvalSettings(opp_deck=tuple(opp_deck), levels=(InfoLevel(rule.level),), max_turn=rule.turn, progress=stage_spec, **cfg_kw)
        cell = run_eval(rules, cand, st, sd).report["cells"][cell_key("d", rule.level, 1.0)]
        if stage_spec is not None:
            return {(s, fp): (kt, stage_value(kt, p[0], p[1], rule.turn))
                    for (s, fp, kt), p in zip(cell["per_game"], cell["per_game_progress"])}
        return {(s, fp): kt for s, fp, kt in cell["per_game"]}

    def score(deck: list[str]) -> dict:
        if workers <= 1 or len(seeds) < 2:
            return one(deck, seeds)
        import multiprocessing as mp
        chunks = [seeds[i::workers] for i in range(workers) if seeds[i::workers]]
        _JOB["fn"], _JOB["deck"], _JOB["chunks"] = one, deck, chunks     # fork で子へ引き継ぐ（クロージャは pickle できない）
        with mp.get_context("fork").Pool(len(chunks)) as pool:
            parts = pool.map(_run_chunk, range(len(chunks)))
        return {k: v for d in parts for k, v in d.items()}
    return score


def decide(base: dict, cand: dict, rule: AcceptRule, unverified: bool) -> dict:
    """同一シード・同一先後の対比較。未確認デッキは常に保留（自動採用しない）。"""
    keys = sorted(set(base) & set(cand))
    if set(base) != set(cand):
        return {"verdict": "invalid", "why": "評価セットが一致しない"}
    f = lambda d: [1.0 if d[k] is not None and d[k] <= rule.turn else 0.0 for k in keys]
    r = paired_diff(f(cand), f(base), alpha=rule.alpha)
    if unverified:
        verdict = "hold_unverified"
    elif r["significant"] and r["diff"] > 0:
        verdict = "accept"
    elif r["significant"]:
        verdict = "reject"
    else:
        verdict = "inconclusive"
    return {"verdict": verdict, "rule": rule.version, "turn": rule.turn, "paired": r}


def record(ledger: str | Path, entry: dict) -> None:
    """採否の記録（追記のみ）。調整用の経路なので split=holdout の記録は書けない（base.store）。"""
    store.append_json(ledger, {"t": time.time(), **entry}, purpose="tuning")
