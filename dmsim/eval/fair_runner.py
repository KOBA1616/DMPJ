"""FAIR の1局（窓口 play_api の game / FAIR）を InfoLevel.FAIR に登録する。
ターンまたぎロック判定(lock_probe)は含めない。比較のため CHEAT 既定も lock_rounds=0 で回す（infolevel 参照）。"""
from __future__ import annotations

from ..play_api import InfoLevel, PlayConfig, play
from .infolevel import register_runner


def make_fair_runner(n_det: int = 8, lookahead: int = 0):
    def run(rules, deck, opp_deck, seed, first_player, max_turn, budget, start=None, opp=None, sink=None):
        cfg = PlayConfig(deck=tuple(deck), opp_deck=tuple(opp_deck), seed=seed, first_player=first_player, max_turn=max_turn,
                         budget=budget, n_det=n_det, lookahead=lookahead, opp=opp)
        r = play(start, cfg, InfoLevel.FAIR, rules=rules)
        if sink is not None:
            sink(r.engine)
        return r.game
    return run


def register(n_det: int = 8, lookahead: int = 0) -> None:
    register_runner(InfoLevel.FAIR, make_fair_runner(n_det, lookahead))
