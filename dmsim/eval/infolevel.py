"""情報水準（観測と決定化）。探索側との唯一の差し替え点。

CHEAT = 真の山札順を見る（教師・診断・上限値のみ）。FAIR = 山札は多重集合から決定化（合否判定はこちら）。
探索側は register_runner(level, fn) で実装を登録する。fn(rules, deck, opp_deck, seed, first_player, max_turn, budget[, start][, opp]) -> GameResult。
opp は dmsim.opponent.OppModel（None/未指定なら何もしない相手）。ハーネスは opp があるときだけ渡す。
"""
from __future__ import annotations

from enum import Enum
from typing import Callable


class InfoLevel(str, Enum):
    CHEAT = "cheat"
    FAIR = "fair"


_RUNNERS: dict[InfoLevel, Callable] = {}


def register_runner(level: InfoLevel, fn: Callable) -> None:
    _RUNNERS[InfoLevel(level)] = fn


def get_runner(level: InfoLevel) -> Callable:
    level = InfoLevel(level)
    if level not in _RUNNERS and level is InfoLevel.CHEAT:
        _register_default_cheat()
    if level not in _RUNNERS and level is InfoLevel.FAIR:
        from .fair_runner import register
        register()
    if level not in _RUNNERS:
        raise NotImplementedError(f"情報水準 {level.value} の探索が未登録（register_runner で登録する）")
    return _RUNNERS[level]


def _register_default_cheat() -> None:
    from ..solitaire import play_game

    def run(rules, deck, opp_deck, seed, first_player, max_turn, budget, start=None, opp=None):
        res, _ = play_game(rules, deck, opp_deck, seed, first_player=first_player, max_turn=max_turn, budget=budget,
                             lock_rounds=0, start=start, opp=opp)  # FAIR と揃える（ロックは別指標）
        return res

    _RUNNERS[InfoLevel.CHEAT] = run
