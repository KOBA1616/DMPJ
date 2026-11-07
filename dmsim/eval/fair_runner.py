"""FairTurnSearch を InfoLevel.FAIR に登録する。play_game と同じ1人回しループ（エンジン・solitaire.py は未編集）。
ターンまたぎロック判定(lock_probe)は含めない。比較のため CHEAT 既定も lock_rounds=0 で回す（infolevel 参照）。"""
from __future__ import annotations

import time

from ..engine.core import Engine
from ..search.fair import FairTurnSearch
from ..solitaire import GameResult, _origin, charge_only_policy, own_turn
from .infolevel import InfoLevel, register_runner


def make_fair_runner(n_det: int = 8):
    def run(rules, deck, opp_deck, seed, first_player, max_turn, budget, start=None, opp=None):
        me = 0
        t0 = time.perf_counter()
        res = GameResult(seed=seed, first_player=first_player)
        eng = start.clone() if start is not None else Engine.new_game(rules, [deck, opp_deck], seed, first_player)
        opp_pol = charge_only_policy
        try:
            if opp is not None:
                opp.setup(eng)
                opp_pol = opp.policy
            while (d := eng.advance()) is not None:
                if eng.s.active != me or d["player"] != me:
                    eng.answer(opp_pol(eng, d))
                    continue
                ot = own_turn(eng, me)
                if ot > max_turn:
                    break
                fs = FairTurnSearch(me, budget, n_det, seed * 7919 + ot, opp_policy=opp_pol)
                eng = fs.run(eng)
                res.nodes += fs.nodes
            r = eng.s.result
            if r is not None:
                if r["winner"] == me:
                    res.kill_turn = own_turn(eng, me, r["turn"])
                    res.kind = r["reason"]
                    res.origin = _origin(res)
                else:
                    res.lost = r["reason"]
        except Exception as ex:
            res.error = f"{type(ex).__name__}: {ex}"
        res.decisions = len(eng.log)
        res.seconds = time.perf_counter() - t0
        return res
    return run


def register(n_det: int = 8) -> None:
    register_runner(InfoLevel.FAIR, make_fair_runner(n_det))
