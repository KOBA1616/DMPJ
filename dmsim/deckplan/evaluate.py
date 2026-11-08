"""採否と評価の接続。測るのは dmsim.eval のハーネス、採否は固定の AcceptRule だけ。

指標と規則は自動で変えない（AcceptRule は凍結した版つき値。変更は人が新しい版を追加する）。
採否の根拠は FAIR 水準の値のみ（CHEAT は上限値として併記するだけ）。"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..eval.stats import paired_diff


@dataclass(frozen=True)
class AcceptRule:
    version: str = "v0"
    turn: int = 4                    # 指標: この手番までのキル率
    level: str = "fair"
    alpha: float = 0.05


# scorer: (デッキ名->ID列, 評価セット) -> {(seed, 先後): キルターン|None}。ハーネス接続は harness_scorer。
Scorer = Callable[[list[str]], "dict[tuple, int | None]"]


def harness_scorer(rules, opp_deck: list[str], seeds: list[int], rule: AcceptRule = AcceptRule(), **cfg_kw) -> Scorer:
    from ..eval.harness import EvalConfig, cell_key, run_eval
    from ..eval.infolevel import InfoLevel

    def score(deck: list[str]) -> dict:
        cfg = EvalConfig(decks={"d": deck}, opp_deck=opp_deck, seeds=seeds, levels=(InfoLevel(rule.level),),
                         max_turn=rule.turn, **cfg_kw)
        cell = run_eval(rules, cfg)["cells"][cell_key("d", rule.level, 1.0)]
        return {(s, fp): kt for s, fp, kt in cell["per_game"]}
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
    """採否の記録（追記のみ）。"""
    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": time.time(), **entry}, ensure_ascii=False) + "\n")
