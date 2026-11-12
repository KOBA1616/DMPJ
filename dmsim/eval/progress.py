"""段階指標（途中の到達）。勝ち/負けの0-1ではなく、自分の各ターン終了時の盤面を記録して連続・順序つきの指標にする。

- ProgressSpec.board : 最小盤面M。{ゾーン: {カード定義ID: 枚数}}（自分側）。全部満たした最初の自分のターン（0=開始時）が board_turn
- ProgressSpec.cards : 必要カード {定義ID: 枚数}。山札・盾以外の自分側ゾーン（=自分が見える/使える所）にそろった最初のターンが cards_turn
- 毎ターン終了時の曲線: opp_shield / opp_deck / own_gy / own_hand / own_mana / own_bz（相手の残盾・残山札が減るほど前進）
未到達は None。集計側（harness）で max_turn+1 として打ち切り扱いにする。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..engine.core import Engine
from ..search.game import GameResult
from ..search.game import origin as _origin
from ..play_api import PlayConfig, play_turns
from ..search.turn import charge_only_policy, own_turn
from .infolevel import InfoLevel
from .stage import VISIBLE_ZONES, board_met, cards_met, zone_counts  # noqa: F401  段階指標の共通部品
from ..engine.view import result_of


@dataclass(frozen=True)
class ProgressSpec:
    board: dict = field(default_factory=dict)   # {zone: {defn: n}}
    cards: dict = field(default_factory=dict)   # {defn: n}


@dataclass
class ProgressResult(GameResult):
    board_turn: int | None = None
    cards_turn: int | None = None
    curve: list = field(default_factory=list)   # [{turn, opp_shield, opp_deck, own_gy, own_hand, own_mana, own_bz}]


_count = zone_counts


def snapshot(eng: Engine, me: int, turn: int) -> dict:
    n = lambda z, p: len(eng.zlist(z, p))
    return {"turn": turn, "opp_shield": n("shield", 1 - me), "opp_deck": n("deck", 1 - me), "own_gy": n("graveyard", me),
            "own_hand": n("hand", me), "own_mana": n("mana", me), "own_bz": n("bz", me),
            "gy_defs": dict(zone_counts(eng, me, "graveyard")),
            "defs": {z: dict(zone_counts(eng, me, z)) for z in ("hand", "bz", "mana", "graveyard")}}   # 部品の自動発見用（最終局面の自分側の見えるゾーン）


def board_ok(eng: Engine, me: int, spec: ProgressSpec) -> bool:
    return board_met(eng, me, spec.board)


def cards_ok(eng: Engine, me: int, spec: ProgressSpec) -> bool:
    return cards_met(eng, me, spec.cards)


def make_progress_runner(level: InfoLevel, spec: ProgressSpec, n_det: int = 8, value_fn=None, lookahead: int = 0):
    """InfoLevel の runner と同じ署名。自分のターンごとに盤面を記録する以外は solitaire.play_game(lock_rounds=0) と同じ回し方。"""
    level = InfoLevel(level)

    def run(rules, deck, opp_deck, seed, first_player, max_turn, budget, start=None, opp=None, sink=None):
        me = 0
        t0 = time.perf_counter()
        res = ProgressResult(seed=seed, first_player=first_player)
        eng = start.clone() if start is not None else Engine.new_game(rules, [deck, opp_deck], seed, first_player)
        opp_pol = charge_only_policy
        if opp is not None:
            opp.setup(eng)
            opp_pol = opp.policy

        def record(turn):
            if spec.board and res.board_turn is None and board_ok(eng, me, spec):
                res.board_turn = turn
            if spec.cards and res.cards_turn is None and cards_ok(eng, me, spec):
                res.cards_turn = turn
            res.curve.append(snapshot(eng, me, turn))

        try:
            eng.advance()
            record(0)
            cfg = PlayConfig(seed=seed, max_turn=max_turn, budget=budget, n_det=n_det, lookahead=lookahead,
                             value_fn=value_fn, me=me)
            holder = [eng]

            def on_turn(e, ot, nodes):
                nonlocal eng
                eng = e
                res.nodes += nodes
                record(ot)

            try:
                eng = play_turns(eng, cfg, level, opp_policy=opp_pol, on_turn=on_turn, holder=holder)
            finally:
                eng = holder[0]
            r = result_of(eng)
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
        if sink is not None:
            sink(eng)
        return res

    return run
