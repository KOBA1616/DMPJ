"""評価の窓口 run_eval（S4、ロードマップ P0-2）。

S5 発見・S6 学習改善・tools は eval の内部（harness・fair_runner・infolevel の登録）を直接呼ばずにここを通す。
    run_eval(候補, 評価設定, 局数) -> EvalResult
中身は eval.harness.run_eval の薄い包み。採否に使う値（win_rate・reach 系）は FAIR のセルからだけ出す。
CHEAT を levels に入れても上限値として report に載るだけ。V（評価関数）は順位づけ補助で、ここでは足切りに使わない。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from ..play_api import InfoLevel
from . import lockcheck  # noqa: F401  （import 時に play_game の既定のロック判定役 lock_probe を登録する）

API_VERSION = 1


@dataclass(frozen=True)
class Candidate:
    """評価する候補。デッキ（必須）と、あればコンボ名・開始局面の spec。"""
    deck: tuple[str, ...]
    name: str = "d"
    combo: str | None = None
    start_spec: dict | None = None         # dmsim.scenario.build の spec（各シードでその局面から始める）
    version: int = API_VERSION


@dataclass(frozen=True)
class EvalSettings:
    """評価設定（不変）。項目は eval.harness.EvalConfig と同じ意味。"""
    opp_deck: tuple[str, ...]
    levels: tuple[InfoLevel, ...] = (InfoLevel.FAIR,)
    max_turn: int = 4
    target_turn: int | None = None         # T内勝率の T（None なら max_turn）
    base_budget: int = 200
    budget_mults: tuple[float, ...] = (1.0,)
    first: str = "both"
    n_det: int = 8                         # FAIR の決定化数
    lookahead: int = 0                     # FAIR の複数ターン探索
    register_fair: bool = False            # True: 既定の FAIR 探索を (n_det, fair_lookahead) で登録し直してから回す（従来の fair_runner.register と同じ）
    fair_lookahead: int | None = None      # 登録する FAIR 探索の複数ターン予算（None なら lookahead）。progress 側の lookahead と別に決める従来の呼び方用
    progress: Any = None                   # eval.progress.ProgressSpec（段階指標＝到達層）
    value_fn: Callable | None = None
    opps: dict | None = None               # 名前 -> OppModel|None
    level_mult: dict | None = None
    match_nodes: bool = False
    explog: Any = None
    known_combos: dict | None = None
    version: int = API_VERSION


@dataclass
class EvalResult:
    """評価結果。出せない項目は None（reproducibility・cost_perf・exec_layer は現状未接続）。"""
    win_rate: float | None                 # FAIR の T内勝率（自分の target_turn ターン目までに勝った割合）
    win_rate_ci95: list | None
    win_rate_by_turn: dict                 # FAIR: {ターン: 率}
    reproducibility: float | None          # 再現性確率（未接続: None）
    cost_perf: float | None                # コスト対パフォーマンス（未接続: None。eval.cost_perf は探索の順位づけ項）
    reach_layer: dict | None               # 到達層: progress 指定時の {board_turn/cards_turn: 到達率}
    exec_layer: dict | None                # 実行層（未接続: None。tools/reach_table 等が別に測る）
    games: int
    per_game: list                         # FAIR: [[seed, 先後, キルターン|None], ...]
    per_game_progress: list
    report: dict                           # harness.run_eval の生の報告（CHEAT の上限値を含む）
    cell_key: str | None
    version: int = API_VERSION


def _seeds(games) -> list[int]:
    if isinstance(games, int):
        return list(range(1, games + 1))
    return list(games)


def run_eval(rules, cand: Candidate, settings: EvalSettings, games: int | Sequence[int]) -> EvalResult:
    """候補を評価する。games は局数（シード 1..n）またはシードの並び（先後 both なら局数はその2倍）。"""
    from . import fair_runner
    from .harness import EvalConfig, cell_key
    from .harness import run_eval as _harness_run
    if settings.register_fair:
        fair_runner.register(settings.n_det, settings.lookahead if settings.fair_lookahead is None else settings.fair_lookahead)
    kw: dict = {}
    for k in ("opps", "level_mult", "known_combos"):
        v = getattr(settings, k)
        if v is not None:
            kw[k] = v
    cfg = EvalConfig(decks={cand.name: list(cand.deck)}, opp_deck=list(settings.opp_deck), seeds=_seeds(games),
                     levels=tuple(settings.levels), budget_mults=tuple(settings.budget_mults), base_budget=settings.base_budget,
                     max_turn=settings.max_turn, first=settings.first, start_spec=cand.start_spec, progress=settings.progress,
                     match_nodes=settings.match_nodes, lookahead=settings.lookahead, n_det=settings.n_det,
                     value_fn=settings.value_fn, explog=settings.explog, **kw)
    report = _harness_run(rules, cfg)
    key = cell_key(cand.name, InfoLevel.FAIR, settings.budget_mults[0]) if InfoLevel.FAIR in tuple(map(InfoLevel, settings.levels)) else None
    cell = report["cells"].get(key) if key else None
    if cell is None:
        return EvalResult(None, None, {}, None, None, None, None, 0, [], [], report, None)
    T = settings.target_turn or settings.max_turn
    kbt = cell.get("kill_rate_by_turn", {})
    kr = kbt.get(T)
    reach = None
    if "progress" in cell:
        reach = {k: cell["progress"][k]["reach_rate"] for k in ("board_turn", "cards_turn")}
    return EvalResult(win_rate=kr["rate"] if kr else None, win_rate_ci95=kr["ci95"] if kr else None,
                      win_rate_by_turn={t: v["rate"] for t, v in kbt.items()},
                      reproducibility=None, cost_perf=None, reach_layer=reach, exec_layer=None,
                      games=cell.get("games", len(cell["per_game"])), per_game=cell["per_game"], per_game_progress=cell.get("per_game_progress", []),
                      report=report, cell_key=key)


def measure_assembly(rules, entry: str, deck, seeds, *, max_turn: int = 6, budget: int = 200, n_det: int = 8,
                     route: str | None = None, route_log: str | None = None, route_opts: dict | None = None) -> list[dict]:
    """「揃う」と入口到達の測定の窓口（eval.assemble.run_one の薄い包み、通常開幕・FAIR）。デッキ構築（S5）がここを通す。
    戻り値は局ごとの {seed, cards_turn（使えるゾーンだけで数える）, cards_turn_any（旧い数え方）, entry_turn, stage_turn,
    stage2, via, kill, beat, win_turn, kind}（未到達は None）。route / route_log / route_opts は assemble.run_one と同じ。"""
    from . import assemble
    from . import loop_entry as L
    ls = L.load(entry) if isinstance(entry, str) else entry    # LoopSpec をそのまま渡してもよい（ファイルに無い入口、2026-11-14）
    out = []
    for s in seeds:
        r = assemble.run_one(rules, ls, s, deck=list(deck), max_turn=max_turn, budget=budget, n_det=n_det,
                             route=route, route_log=route_log, route_opts=route_opts)
        v = r["verdict"].stage2
        out.append({"seed": s, "cards_turn": r["cards_turn"], "cards_turn_any": r["cards_turn_any"], "entry_turn": r["entry_turn"],
                    "stage_turn": r["stage_turn"], "stage2": v.ok, "via": v.via, "kill": v.kill, "beat": v.beat_win,
                    "win_turn": v.win_turn, "kind": r["res"].kind, "error": r["res"].error})
    return out
