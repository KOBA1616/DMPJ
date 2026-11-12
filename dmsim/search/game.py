"""1局の進行（S3、P0-3 で solitaire.py から分割）。CHEAT の play_game（TurnSearch＋ロック判定）と FAIR の fair_game
（FairTurnSearch）は、共通の手番ループ run_turns を使う。

ロックの試し回し round_probe / lock_probe は構造検証に当たるが、play_game が毎ターン使うので S3 に残す（S4 構造検証の新設は P2）。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..engine import Engine
from ..loop import LoopCertificate, LoopDetector, verify
from ..play import passive_policy
from .leaf_eval import Weights
from .turn import TurnSearch, charge_only_policy, own_turn


@dataclass
class GameResult:
    seed: int
    first_player: int
    kill_turn: int | None = None      # 自分の何ターン目に勝ち（またはロック確立）
    origin: str | None = None         # lock / loop（ループで山札・シールドを削った）/ engine（資源ループの後に殴った・決めた）/ combat / effect
    kind: str | None = None           # direct_attack / deck_out / loop_deck_out / effect / lock
    lost: str | None = None           # 自分が負けた理由（deck_out など）
    loops: list[dict] = field(default_factory=list)
    lock: dict | None = None
    nodes: int = 0
    decisions: int = 0
    seconds: float = 0.0
    error: str | None = None


def lock_ok(cert: LoopCertificate, me: int) -> bool:
    """相手の資源が周回ごとに増えない（山札と墓地以外の相手側カウンタの差分が 0 以下）ロックだけを認める。"""
    opp = f":{1 - me}"
    grows = any(v > 0 for k, v in cert.delta.items()
                if k.endswith(opp) and not k.startswith(("deck:", "graveyard:")))
    return cert.win_by == "opp_deck_out" and not grows



def origin(res: GameResult) -> str:
    """勝ち方の由来。ループで相手の山札・シールドを削ってから決めたものを、殴り勝ちや効果だけの勝ちと分ける。"""
    if any(lp["win_by"] for lp in res.loops):
        return "loop"
    if res.loops:
        return "engine"
    return "combat" if res.kind == "direct_attack" else "effect"


_lock_ok = lock_ok    # 旧名（互換）
_origin = origin      # 旧名（互換）


def round_probe(eng: Engine, me: int, rounds: int = 2) -> LoopCertificate | None:
    """自分が何もしなくなっても、ターン開始・終了の誘発などで毎ラウンド同じ骨格に戻る周期（時計）を見つける。
    ロックかどうか（相手が動けないか）は見ない。それは lock_probe が lock_ok で絞る。"""
    e = eng.clone()
    det = LoopDetector(me=me, period="round", hand_keys=set(), report_all=True)
    seen_turns, last = 0, None
    while (d := e.advance()) is not None:
        if e.s.active == me and d["player"] == me and e.s.turn != last:
            last = e.s.turn
            seen_turns += 1
            cert = det.observe(e)
            if cert is not None:
                return cert if verify(e, cert, times=2).verified == 2 else None
            if seen_turns > rounds:
                return None
        e.answer(passive_policy(e, d) if d["player"] == me else charge_only_policy(e, d))
    return None


def lock_probe(eng: Engine, me: int, rounds: int = 2) -> LoopCertificate | None:
    """「ここで自分が何もしなくなっても、相手は山札切れまで何もできないか」を確かめる。
    自分は何もしない（passive）、相手はマナチャージだけして rounds+1 周回し、ラウンド周期の骨格の回帰を探す。
    自分が動き続ける本番の対戦では骨格が毎ターン変わるので、ロックはこの別の試し回しで見る。"""
    cert = round_probe(eng, me, rounds)
    return cert if cert is not None and lock_ok(cert, me) else None



def run_turns(cur: list, me: int, max_turn: int, opp_pol, take_turn) -> None:
    """1局の手番ループ。cur[0] の Engine を進め、自分の決定になったら自分の何ターン目か（ot）で take_turn(eng, ot) を呼ぶ。
    take_turn は (次の Engine, 打ち切るか) を返す。自分の max_turn ターン目を過ぎるか終局で止まる。
    cur[0] は常に最新の局面（途中で例外が出ても呼び出し側が最新の局面を見られるよう、入れ物で受け渡す）。"""
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


def play_game(rules, deck: list[str], opp_deck: list[str], seed: int, *, first_player: int = 0,
              max_turn: int = 4, budget: int = 200, weights: Weights | None = None,
              lock_rounds: int = 2, start: Engine | None = None, opp=None, value_fn=None) -> tuple[GameResult, Engine]:
    """自分 = プレイヤー0。自分の max_turn ターン目が終わるまで回す。各ターンの後に lock_probe でロックを確かめる。
    start（dmsim.scenario.build で作った局面など）を渡すとそこから始める（deck / opp_deck / seed は使わない）。"""
    me = 0
    t0 = time.perf_counter()
    res = GameResult(seed=seed, first_player=first_player)
    eng = start.clone() if start is not None else Engine.new_game(rules, [deck, opp_deck], seed, first_player)
    opp_pol = charge_only_policy
    if opp is not None:                      # 妨害モデル（dmsim.opponent.OppModel）。None なら従来の何もしない相手
        opp.setup(eng)
        opp_pol = opp.policy
    search = TurnSearch(me, budget, weights, opp_policy=opp_pol, value_fn=value_fn)

    def take_turn(eng, ot):
        eng, st = search.run(eng)
        res.nodes += st.nodes
        res.loops += [dict(lp, own_turn=ot) for lp in st.loops]
        if eng.s.result is None and lock_rounds > 0:
            cert = lock_probe(eng, me, lock_rounds)
            if cert is not None:
                res.kind, res.kill_turn = "lock", ot
                res.lock = {"delta": cert.delta, "needed_rounds": cert.needed, "limit": cert.limit}
                return eng, True
        return eng, False

    cur = [eng]
    try:
        run_turns(cur, me, max_turn, opp_pol, take_turn)
        eng = cur[0]
        r = eng.s.result
        if res.kind == "lock":
            res.origin = "lock"
        if r is not None and res.kind is None:
            if r["winner"] == me:
                res.kill_turn = own_turn(eng, me, r["turn"])
                res.kind = r["reason"]
                if r["reason"] == "deck_out" and any(lp["win_by"] == "opp_deck_out" for lp in res.loops):
                    res.kind = "loop_deck_out"
                res.origin = origin(res)
            elif r["winner"] == 1 - me:
                res.lost = r["reason"]
    except Exception as ex:          # 1局の失敗で全体を止めない。seed で再現できる
        res.error = f"{type(ex).__name__}: {ex}"
    eng = cur[0]
    res.decisions = len(eng.log)
    res.seconds = time.perf_counter() - t0
    return res, eng


def fair_game(rules, deck, opp_deck, seed, first_player, max_turn, budget, start=None, opp=None,
              n_det: int = 8, lookahead: int = 0):
    """FAIR の1局（FairTurnSearch の1人回し。ロック判定 lock_probe は含めない）。(GameResult, Engine) を返す。"""
    from .fair import FairTurnSearch
    me = 0
    t0 = time.perf_counter()
    res = GameResult(seed=seed, first_player=first_player)
    eng = start.clone() if start is not None else Engine.new_game(rules, [deck, opp_deck], seed, first_player)
    cur = [eng]
    try:
        opp_pol = charge_only_policy
        if opp is not None:
            opp.setup(eng)
            opp_pol = opp.policy

        def take_turn(eng, ot):
            fs = FairTurnSearch(me, budget, n_det, seed * 7919 + ot, opp_policy=opp_pol, lookahead=lookahead)
            eng = fs.run(eng)
            res.nodes += fs.nodes
            return eng, False

        run_turns(cur, me, max_turn, opp_pol, take_turn)
        eng = cur[0]
        r = eng.s.result
        if r is not None:
            if r["winner"] == me:
                res.kill_turn = own_turn(eng, me, r["turn"])
                res.kind = r["reason"]
                res.origin = origin(res)
            else:
                res.lost = r["reason"]
    except Exception as ex:
        res.error = f"{type(ex).__name__}: {ex}"
    eng = cur[0]
    res.decisions = len(eng.log)
    res.seconds = time.perf_counter() - t0
    return res, eng
