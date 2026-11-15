"""1局の進行（S3、P0-3 で solitaire.py から分割）。CHEAT の play_game（TurnSearch＋ロック判定）と FAIR の fair_game
（FairTurnSearch）は、共通の手番ループ run_turns を使う。

ロックの試し回し round_probe / lock_probe / lock_ok は S4 の dmsim.eval.lockcheck へ移した（P2 タスク2）。
play_game は判定役 lock_judge(eng, me, rounds) を引数で受け取る。省略時は lockcheck が import 時に登録した lock_probe を使う。
"""
from __future__ import annotations

from ..engine import rustcore

import time
from dataclasses import dataclass, field
from typing import Callable

from ..engine import Engine
from ..engine.loop import LoopCertificate
from .leaf_eval import Weights
from .pattern_loop import find as find_pattern_loops
from .turn import TurnSearch, charge_only_policy, own_turn


@dataclass
class GameResult:
    seed: int
    first_player: int
    kill_turn: int | None = None      # 自分の何ターン目に勝ち（またはロック確立）
    origin: str | None = None         # lock / loop（ループで山札・シールドを削った）/ engine（資源ループの後に殴った・決めた）/ combat / effect
    kind: str | None = None           # direct_attack / deck_out / loop_deck_out / effect / lock
    lost: str | None = None           # 自分が負けた理由（deck_out など）
    loops: list[dict] = field(default_factory=list)            # 採った手順で使ったループだけ（証明書 source=certificate／繰り返しの記録 source=pattern）
    loop_candidates: list[dict] = field(default_factory=list)  # 探索で試したループの候補すべて（選ばなかった線を含む。旧 loops の中身）
    lock: dict | None = None
    nodes: int = 0
    decisions: int = 0
    seconds: float = 0.0
    error: str | None = None
    opp: str = "none"                 # 相手の抵抗の段階（search.opponent.resistance の名前。"none" は無抵抗）


def origin(res: GameResult) -> str:
    """勝ち方の由来。ループで相手の山札・シールドを削ってから決めたものを、殴り勝ちや効果だけの勝ちと分ける。"""
    if any(lp["win_by"] for lp in res.loops):
        return "loop"
    if res.loops:
        return "engine"
    return "combat" if res.kind == "direct_attack" else "effect"


_origin = origin      # 旧名（互換）


LockJudge = Callable[[Engine, int, int], "LoopCertificate | None"]
_default_lock_judge: LockJudge | None = None


def set_default_lock_judge(fn: LockJudge | None) -> None:
    """play_game の既定のロック判定役を登録する（S4 の dmsim.eval.lockcheck が import 時に lock_probe を登録する）。
    S3 は S4 を import できないので、既定値はこの登録で受け取る。"""
    global _default_lock_judge
    _default_lock_judge = fn


def _resolve_lock_judge(lock_judge: LockJudge | None) -> LockJudge:
    fn = lock_judge if lock_judge is not None else _default_lock_judge
    if fn is None:
        raise RuntimeError("ロック判定役が未登録。dmsim.eval.lockcheck を import するか lock_judge を渡すか lock_rounds=0 にする")
    return fn


def run_turns(cur: list, me: int, max_turn: int, opp_pol, take_turn) -> None:
    """1局の手番ループ。cur[0] の Engine を進め、自分の決定になったら自分の何ターン目か（ot）で take_turn(eng, ot) を呼ぶ。
    take_turn は (次の Engine, 打ち切るか) を返す。自分の max_turn ターン目を過ぎるか終局で止まる。
    cur[0] は常に最新の局面（途中で例外が出ても呼び出し側が最新の局面を見られるよう、入れ物で受け渡す）。"""
    from . import defense
    opp_pol = defense.wrap(opp_pol, me)
    eng = cur[0]
    while (d := eng.advance()) is not None:
        if eng.s.active != me or d["player"] != me:
            eng.answer(opp_pol(eng, d))
            continue
        ot = own_turn(eng, me)
        if ot > max_turn:
            break
        eng, stop = take_turn(eng, ot)
        cur[0] = eng
        if stop:
            break


def record_turn_loops(res: GameResult, before: Engine, after: Engine, at: int, chosen, candidates, ot: int, me: int,
                      pattern_loops: bool = True) -> None:
    """1ターン分のループの記録を res に足す（play_game・fair_game・play_api.play_turns 共通）。局面は変えない。
    chosen（採った手順で使った証明書のループ）があればそれを、無ければ実際に指した記録 after.log[at:] にパターン検出をかける。"""
    res.loop_candidates += [dict(lp, own_turn=ot) for lp in candidates]
    res.loops += [dict(lp, own_turn=ot) for lp in chosen]
    if pattern_loops and not chosen:
        res.loops += [dict(lp, own_turn=ot) for lp in find_pattern_loops(before, after.log[at:], me, at)]


def check_lock(res: GameResult, eng: Engine, ot: int, me: int, judge, lock_rounds: int) -> bool:
    """判定役 judge でロックを確かめ、成立なら res に記録して True（打ち切り）。judge が None なら何もしない。"""
    if judge is None or eng.s.result is not None or lock_rounds <= 0:
        return False
    cert = judge(eng, me, lock_rounds)
    if cert is None:
        return False
    res.kind, res.kill_turn = "lock", ot
    res.lock = {"delta": cert.delta, "needed_rounds": cert.needed, "limit": cert.limit}
    return True


def finish_result(res: GameResult, eng: Engine, me: int) -> None:
    """終局の勝敗を res に書く（play_game・fair_game 共通）。"""
    if res.kind == "lock":
        res.origin = "lock"
    r = eng.s.result
    if r is not None and res.kind is None:
        if r["winner"] == me:
            res.kill_turn = own_turn(eng, me, r["turn"])
            res.kind = r["reason"]
            if r["reason"] == "deck_out" and any(lp["win_by"] == "opp_deck_out" for lp in res.loops):
                res.kind = "loop_deck_out"
            res.origin = origin(res)
        elif r["winner"] == 1 - me:
            res.lost = r["reason"]


def play_game(rules, deck: list[str], opp_deck: list[str], seed: int, *, first_player: int = 0,
              max_turn: int = 4, budget: int = 200, weights: Weights | None = None,
              lock_rounds: int = 2, start: Engine | None = None, opp=None, value_fn=None,
              lock_judge: LockJudge | None = None, pattern_loops: bool = True) -> tuple[GameResult, Engine]:
    """自分 = プレイヤー0。自分の max_turn ターン目が終わるまで回す。各ターンの後に判定役 lock_judge（既定 dmsim.eval.lockcheck.lock_probe）でロックを確かめる。
    start（dmsim.scenario.build で作った局面など）を渡すとそこから始める（deck / opp_deck / seed は使わない）。"""
    me = 0
    t0 = time.perf_counter()
    res = GameResult(seed=seed, first_player=first_player)
    eng = start.clone() if start is not None else Engine.new_game(rules, [deck, opp_deck], seed, first_player)
    eng = rustcore.maybe_rust(eng)   # 全札が Rust で動く局は Rust で進める（既定で有効。DMSIM_RUST=0 で無効。未対応に当たれば Python に戻る）
    opp_pol = charge_only_policy
    if opp is not None:                      # 妨害モデル（dmsim.opponent.OppModel）。None なら従来の何もしない相手
        opp.setup(eng)
        opp_pol = opp.policy
    search = TurnSearch(me, budget, weights, opp_policy=opp_pol, value_fn=value_fn)
    judge = _resolve_lock_judge(lock_judge) if lock_rounds > 0 else None

    def take_turn(eng, ot):
        before, at = eng, len(eng.log)
        eng, st = search.run(eng)
        res.nodes += st.nodes
        record_turn_loops(res, before, eng, at, st.chosen, st.loops, ot, me, pattern_loops)
        return eng, check_lock(res, eng, ot, me, judge, lock_rounds)

    cur = [eng]
    try:
        run_turns(cur, me, max_turn, opp_pol, take_turn)
        finish_result(res, cur[0], me)
    except Exception as ex:          # 1局の失敗で全体を止めない。seed で再現できる
        res.error = f"{type(ex).__name__}: {ex}"
    eng = cur[0]
    res.decisions = len(eng.log)
    res.seconds = time.perf_counter() - t0
    return res, eng


def fair_game(rules, deck, opp_deck, seed, first_player, max_turn, budget, start=None, opp=None,
              n_det: int = 8, lookahead: int = 0, *, lock_judge: LockJudge | None = None, lock_rounds: int = 0,
              pattern_loops: bool = True):
    """FAIR の1局（FairTurnSearch の1人回し）。(GameResult, Engine) を返す。
    ループの記録（P2 案 F）: 採った手に投票した決定化の探索が使った証明書のループ（evidence=determinized）と、
    それが無いターンは実際に指した手順のパターン検出（evidence=executed）を GameResult.loops に残す。手順・勝敗は変えない。
    ロック判定は既定でしない（lock_rounds=0）。lock_rounds>0 なら lock_judge（省略時は登録済みの既定）で確かめる。"""
    from .fair import FairTurnSearch
    me = 0
    t0 = time.perf_counter()
    res = GameResult(seed=seed, first_player=first_player)
    eng = start.clone() if start is not None else Engine.new_game(rules, [deck, opp_deck], seed, first_player)
    eng = rustcore.maybe_rust(eng)   # 全札が Rust で動く局は Rust で進める（既定で有効。DMSIM_RUST=0 で無効。未対応に当たれば Python に戻る）
    cur = [eng]
    try:
        opp_pol = charge_only_policy
        if opp is not None:
            opp.setup(eng)
            opp_pol = opp.policy

        judge = _resolve_lock_judge(lock_judge) if lock_rounds > 0 else None

        def take_turn(eng, ot):
            before, at = eng, len(eng.log)
            fs = FairTurnSearch(me, budget, n_det, seed * 7919 + ot, opp_policy=opp_pol, lookahead=lookahead)
            eng = fs.run(eng)
            res.nodes += fs.nodes
            record_turn_loops(res, before, eng, at, fs.chosen, fs.loops, ot, me, pattern_loops)
            return eng, check_lock(res, eng, ot, me, judge, lock_rounds)

        run_turns(cur, me, max_turn, opp_pol, take_turn)
        finish_result(res, cur[0], me)
        r = cur[0].s.result
        if r is not None and r["winner"] is None:      # 従来どおり引き分け系（step_limit など）も lost に書く
            res.lost = r["reason"]
    except Exception as ex:
        res.error = f"{type(ex).__name__}: {ex}"
    eng = cur[0]
    res.decisions = len(eng.log)
    res.seconds = time.perf_counter() - t0
    return res, eng
