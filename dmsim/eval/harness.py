"""評価ハーネス: 固定シード集合 × 予算倍率 × デッキ × 情報水準 で、ターン別キル率・既知コンボ再発見率・ノード数を測る。

採否は FAIR の値で行う。CHEAT は上限値として併記するだけ（verdict は FAIR のみから出す）。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from .infolevel import InfoLevel, get_runner
from .stats import boot_ci, paired_diff


@dataclass
class EvalConfig:
    decks: dict[str, list[str]]                      # 名前 -> デッキ
    opp_deck: list[str]
    seeds: list[int]
    levels: tuple[InfoLevel, ...] = (InfoLevel.FAIR, InfoLevel.CHEAT)
    budget_mults: tuple[float, ...] = (1.0,)
    base_budget: int = 200
    max_turn: int = 4
    first: str = "both"                              # first / second / both
    known_combos: dict[str, Callable] = field(default_factory=dict)  # 名前 -> fn(GameResult)->bool（再発見の判定）


def _cell(results, cfg: EvalConfig) -> dict:
    n = len(results)
    out = {"games": n, "kill_rate_by_turn": {}, "mean_nodes": sum(r.nodes for r in results) / n if n else 0.0}
    for t in range(1, cfg.max_turn + 1):
        xs = [1.0 if (r.kill_turn is not None and r.kill_turn <= t) else 0.0 for r in results]
        m, lo, hi = boot_ci(xs)
        out["kill_rate_by_turn"][t] = {"rate": m, "ci95": [lo, hi]}
    out["combo_rediscovery"] = {}
    for name, fn in cfg.known_combos.items():
        xs = [1.0 if fn(r) else 0.0 for r in results]
        m, lo, hi = boot_ci(xs)
        out["combo_rediscovery"][name] = {"rate": m, "ci95": [lo, hi]}
    out["per_game"] = [[r.seed, r.first_player, r.kill_turn] for r in results]
    return out


def run_eval(rules, cfg: EvalConfig) -> dict:
    fps = {"first": [0], "second": [1], "both": [0, 1]}[cfg.first]
    report: dict = {"seeds": list(cfg.seeds), "max_turn": cfg.max_turn, "cells": {}}
    for dname, deck in cfg.decks.items():
        for lv in cfg.levels:
            runner = get_runner(lv)
            for bm in cfg.budget_mults:
                t0 = time.perf_counter()
                res = [runner(rules, deck, cfg.opp_deck, s, fp, cfg.max_turn, max(1, int(cfg.base_budget * bm)))
                       for s in cfg.seeds for fp in fps]
                cell = _cell(res, cfg)
                cell["seconds"] = time.perf_counter() - t0
                report["cells"][f"{dname}|{InfoLevel(lv).value}|x{bm}"] = cell
    return report


def kill_vector(cell: dict, turn: int) -> list[float]:
    """同一シード順のキル有無ベクトル（対比較用）。"""
    return [1.0 if (k is not None and k <= turn) else 0.0 for _, _, k in cell["per_game"]]


def compare(report_a: dict, report_b: dict, key: str, turn: int) -> dict:
    """同一シードの対比較。FAIR 側のセルどうしを渡すこと。"""
    return paired_diff(kill_vector(report_a["cells"][key], turn), kill_vector(report_b["cells"][key], turn))


def hidden_info_cost(report: dict, deck: str, turn: int, mult: float = 1.0) -> dict:
    """隠れ情報のコスト = CHEAT - FAIR のキル率差（同一シード対比較）。"""
    c = report["cells"][f"{deck}|cheat|x{mult}"]
    f = report["cells"][f"{deck}|fair|x{mult}"]
    return paired_diff(kill_vector(c, turn), kill_vector(f, turn))
