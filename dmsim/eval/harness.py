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
    start_spec: dict | None = None                   # dmsim.scenario.build の spec。あれば各シードでその局面から始める
    opps: dict = field(default_factory=lambda: {"none": None})  # 名前 -> OppModel|None（相手モデルの差し替え点。dmsim.opponent.PRESETS）
    progress: object | None = None                   # dmsim.eval.progress.ProgressSpec。あれば段階指標を記録し集計する
    level_mult: dict = field(default_factory=dict)   # 水準別の予算倍率 {InfoLevel: x}（探索量をそろえる比較用。例 CHEAT を n_det 倍）
    match_nodes: bool = False                        # True: CHEAT の予算倍率を FAIR の平均ノード数に合うよう自動調整する（level_mult は初期値）
    match_pilot: int = 8                             # 調整に使う試験局数
    match_tol: float = 0.1                           # 目標との許容誤差（比）
    n_det: int = 8                                   # progress 指定時の FAIR の決定化数
    explog: object | None = None                     # dmsim.eval.steplog.ExpLogSpec。あれば各セルの先頭の局を1手ごとに版つきJSONLへ記録する
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
    if results and hasattr(results[0], "curve"):
        out["progress"] = _progress_cell(results, cfg)
    out["per_game"] = [[r.seed, r.first_player, r.kill_turn] for r in results]
    if results and hasattr(results[0], "curve"):
        out["per_game_progress"] = [[r.board_turn, r.cards_turn, r.curve[-1] if r.curve else None] for r in results]
    return out


def _mean_nodes(results) -> float:
    return sum(r.nodes for r in results) / len(results) if results else 0.0


def _turn_or_cap(t, cfg: EvalConfig) -> float:
    return float(cfg.max_turn + 1 if t is None else t)


def _progress_cell(results, cfg: EvalConfig) -> dict:
    out: dict = {}
    for name in ("board_turn", "cards_turn"):
        vals = [getattr(r, name) for r in results]
        xs = [_turn_or_cap(v, cfg) for v in vals]
        m, lo, hi = boot_ci(xs)
        out[name] = {"reach_rate": sum(v is not None for v in vals) / len(vals), "mean_turn_capped": m, "ci95": [lo, hi]}
    # 毎ターンの曲線（平均）。最終値は「そのターン終了時」の盤面
    keys = ("opp_shield", "opp_deck", "own_gy", "own_hand", "own_mana", "own_bz")
    out["curve_mean"] = {}
    for t in range(0, cfg.max_turn + 1):
        rows = [c for r in results for c in r.curve if c["turn"] == t]
        if rows:
            out["curve_mean"][t] = {k: sum(c[k] for c in rows) / len(rows) for k in keys}
    return out


def _start_kw(rules, cfg: EvalConfig, seed: int, fp: int) -> dict:
    if cfg.start_spec is None:
        return {}
    from ..scenario import build
    start = build(rules, {**cfg.start_spec, "seed": seed}, first_player=fp)
    if cfg.start_spec.get("shuffle_deck"):            # 山札の並びをシードごとに変える（隠れ情報が効く局面用）
        import random
        for p in (0, 1):
            random.Random(seed * 1009 + p).shuffle(start.s.zones["deck"][p])
    return {"start": start}


def cell_key(dname: str, level, mult: float, opp: str = "none") -> str:
    """セル名。相手が既定（none）なら従来どおり、それ以外は末尾に |opp=名前 を付ける。"""
    k = f"{dname}|{InfoLevel(level).value}|x{mult}"
    return k if opp == "none" else f"{k}|opp={opp}"


def calibrate_mult(run_pilot, target_nodes: float, mult: float = 1.0, tol: float = 0.1, iters: int = 4) -> tuple[float, float]:
    """run_pilot(mult)->平均ノード数 を呼び、目標ノード数に近づく予算倍率を探す（比で更新。探索は早期終了するので一般に非線形）。
    戻り値は (倍率, その時の平均ノード数)。許容内に入れば打ち切り、入らなければ最も近かったものを返す。"""
    best, prev = None, None
    for _ in range(iters):
        got = run_pilot(mult)
        if best is None or abs(got - target_nodes) < abs(best[1] - target_nodes):
            best = (mult, got)
        if got <= 0 or abs(got - target_nodes) <= tol * target_nodes:
            break
        k = 1.0                                   # ノード数 ∝ 倍率^k として、直近2点から k を推定（対数空間の割線法）
        if prev is not None and prev[0] != mult and prev[1] > 0:
            import math
            k = min(1.5, max(0.2, math.log(got / prev[1]) / math.log(mult / prev[0])))
        prev = (mult, got)
        mult = max(0.05, mult * min(8.0, max(0.125, (target_nodes / got) ** (1 / k))))
    return best


def run_eval(rules, cfg: EvalConfig) -> dict:
    fps = {"first": [0], "second": [1], "both": [0, 1]}[cfg.first]
    report: dict = {"seeds": list(cfg.seeds), "max_turn": cfg.max_turn, "cells": {}}
    for dname, deck in cfg.decks.items():
        for lv in cfg.levels:
            if cfg.progress is not None:
                from .progress import make_progress_runner
                runner = make_progress_runner(lv, cfg.progress, cfg.n_det)
            else:
                runner = get_runner(lv)
            for oname, opp in cfg.opps.items():
                for bm in cfg.budget_mults:
                    t0 = time.perf_counter()
                    kw = {} if opp is None else {"opp": opp}
                    lm = cfg.level_mult.get(InfoLevel(lv), 1)
                    jobs = [(s, fp) for s in cfg.seeds for fp in fps]

                    engs: dict = {}

                    def run_jobs(mult, jobs=jobs, keep=False):
                        out = []
                        for i, (s, fp) in enumerate(jobs):
                            extra = {}
                            if keep and cfg.explog is not None and i < cfg.explog.max_games_per_cell:
                                extra["sink"] = lambda e, i=i: engs.__setitem__(i, e)
                            out.append(runner(rules, deck, cfg.opp_deck, s, fp, cfg.max_turn,
                                              max(1, int(cfg.base_budget * bm * mult)),
                                              **_start_kw(rules, cfg, s, fp), **kw, **extra))
                        return out

                    calib = None
                    fair_key = cell_key(dname, InfoLevel.FAIR, bm, oname)
                    if cfg.match_nodes and InfoLevel(lv) is InfoLevel.CHEAT and fair_key in report["cells"]:
                        target = report["cells"][fair_key]["mean_nodes"]
                        pilot = jobs[:cfg.match_pilot]
                        lm, got = calibrate_mult(lambda m: _mean_nodes(run_jobs(m, pilot)), target, lm, cfg.match_tol)
                        calib = {"target_nodes": target, "pilot_nodes": got, "mult": lm}
                    res = run_jobs(lm, keep=True)
                    cell = _cell(res, cfg)
                    if cfg.explog is not None:
                        cell["explog"] = _write_explog(rules, cfg, dname, deck, lv, bm, lm, oname, opp, jobs, res, engs)
                    if calib:
                        cell["node_match"] = calib
                    cell["budget_mult_used"] = lm
                    cell["seconds"] = time.perf_counter() - t0
                    report["cells"][cell_key(dname, lv, bm, oname)] = cell
    return report


def _write_explog(rules, cfg: EvalConfig, dname, deck, lv, bm, lm, oname, opp, jobs, res, engs) -> dict:
    from .steplog import CellLogger
    key = cell_key(dname, lv, bm, oname)
    exp_cfg = {"deck": dname, "level": InfoLevel(lv).value, "budget_mult": bm, "opp": oname, "seeds": list(cfg.seeds),
               "base_budget": cfg.base_budget, "max_turn": cfg.max_turn, "first": cfg.first}
    cl = CellLogger(cfg.explog, exp_cfg, key, oname)
    for i, eng in sorted(engs.items()):
        s, fp = jobs[i]
        cl.add_game(rules, eng, res[i], deck, cfg.opp_deck, fp, _start_kw(rules, cfg, s, fp).get("start"), opp)
    out = cl.close()
    out["truncated"] = out["truncated"] or len(jobs) > out["games"]   # 局数上限で記録しなかった局がある
    return out


def kill_vector(cell: dict, turn: int) -> list[float]:
    """同一シード順のキル有無ベクトル（対比較用）。"""
    return [1.0 if (k is not None and k <= turn) else 0.0 for _, _, k in cell["per_game"]]


def compare(report_a: dict, report_b: dict, key: str, turn: int) -> dict:
    """同一シードの対比較。FAIR 側のセルどうしを渡すこと。"""
    return paired_diff(kill_vector(report_a["cells"][key], turn), kill_vector(report_b["cells"][key], turn))


def hidden_info_cost(report: dict, deck: str, turn: int, mult: float = 1.0, opp: str = "none") -> dict:
    """隠れ情報のコスト = CHEAT - FAIR のキル率差（同一シード対比較）。"""
    c = report["cells"][cell_key(deck, "cheat", mult, opp)]
    f = report["cells"][cell_key(deck, "fair", mult, opp)]
    return paired_diff(kill_vector(c, turn), kill_vector(f, turn))


def progress_vector(cell: dict, metric: str, max_turn: int) -> list[float]:
    """同一シード順の段階指標ベクトル。metric: board_turn / cards_turn（未到達は max_turn+1）/ opp_shield / opp_deck / own_gy（最終ターンの値）。"""
    rows = cell["per_game_progress"]
    if metric in ("board_turn", "cards_turn"):
        i = 0 if metric == "board_turn" else 1
        return [float(max_turn + 1 if r[i] is None else r[i]) for r in rows]
    return [float(r[2][metric]) if r[2] else 0.0 for r in rows]


def hidden_info_cost_progress(report: dict, deck: str, metric: str, mult: float = 1.0, opp: str = "none") -> dict:
    """段階指標での隠れ情報コスト = FAIR - CHEAT（到達ターン・残盾は小さいほど良いので、正なら公平のほうが悪い）。"""
    c = report["cells"][cell_key(deck, "cheat", mult, opp)]
    f = report["cells"][cell_key(deck, "fair", mult, opp)]
    mt = report["max_turn"]
    return paired_diff(progress_vector(f, metric, mt), progress_vector(c, metric, mt))
