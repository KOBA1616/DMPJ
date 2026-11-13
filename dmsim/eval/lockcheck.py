"""ロック判定（S4 構造検証、P2 タスク2 で dmsim.search.game から移動）。
round_probe: 自分が何もしなくなってもラウンド周期で骨格が戻るかの試し回し。lock_probe: それが相手を山札切れへ追うロックか。
S3 の play_game は判定役を引数 lock_judge で受け取り、省略時はここで登録する lock_probe を使う。
"""
from __future__ import annotations

from ..engine import Engine
from dataclasses import dataclass, field
from typing import Callable

from ..engine.loop import LoopCertificate, LoopDetector, abstract, verify
from ..engine.play import passive_policy
from ..search.game import set_default_lock_judge
from ..search.turn import charge_only_policy, own_turn


def lock_ok(cert: LoopCertificate, me: int) -> bool:
    """相手の資源が周回ごとに増えない（山札と墓地以外の相手側カウンタの差分が 0 以下）ロックだけを認める。"""
    opp = f":{1 - me}"
    grows = any(v > 0 for k, v in cert.delta.items()
                if k.endswith(opp) and not k.startswith(("deck:", "graveyard:")))
    return cert.win_by == "opp_deck_out" and not grows



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


Policy = Callable[[Engine, dict], list[int]]


@dataclass
class LockRun:
    """ロック成立から最後まで回した結果。ロックは独立した勝ち方ではなく「相手の山札切れ勝ちへの経路」として記録する（設計書 §7）。"""
    set_turn: int                     # ロックが成立した自分の何ターン目か（回し始めの局面）
    won: bool = False                 # 相手の山札切れで自分が勝った
    turns_to_win: int | None = None   # 成立から勝ちまでの自分のターン数
    win_turn: int | None = None       # 勝った自分の何ターン目か
    own_deck_left: int | None = None  # 終了時の自分の山札残り
    broken: str | None = None         # 途中でロックが破れた・勝てなかった理由（None なら勝ち）
    broken_turn: int | None = None    # 破れた・止めた自分の何ターン目か
    result: dict | None = None        # エンジンの終局情報
    opp_growth: dict = field(default_factory=dict)   # 破れた時の相手資源の増分


def opp_resources(eng: Engine, me: int) -> dict[str, int]:
    """相手側の資源カウンタ（山札・墓地を除く）。ロック中にこれが成立時より増えたら破れたとみなす。"""
    opp = f":{1 - me}"
    return {k: v for k, v in abstract(eng, "round", set())[1].items()
            if k.endswith(opp) and not k.startswith(("deck:", "graveyard:"))}


def prefer_policy(*prefixes: str) -> Policy:
    """能動ロック用の自分の方針: 選択肢の key が prefixes のどれかで始まればそれを選び、なければ何もしない（passive）。
    例 prefer_policy("play:dm16-051") は毎ターン使えるだけドリル・スコールを唱える。"""
    def pol(eng: Engine, d: dict) -> list[int]:
        keys = [o["key"] for o in d["options"]]
        for pre in prefixes:
            for i, k in enumerate(keys):
                if k.startswith(pre):
                    return [i]
        return passive_policy(eng, d)
    return pol


def run_lock_to_end(eng: Engine, me: int, *, my_policy: Policy | None = None, opp_policy: Policy | None = None,
                    max_turns: int = 80, slack: int = 0) -> LockRun:
    """ロック成立後の局面 eng から、相手の山札切れ（または自分の山札切れ・その他の終局）まで実際に回す。
    自分は my_policy（既定 passive = 何もしない。能動ロックは prefer_policy などを渡す）、相手は opp_policy（既定マナチャージだけ）。
    破れの判定: 自分のターン開始ごとに相手の資源（山札・墓地以外）を成立の次の自分のターン開始時（一巡後）と比べ、slack を超えて増えたら破れ。
    勝敗はエンジンの終局判定に従う（両者同時の山札切れはターンプレイヤーの敗北）。"""
    e = eng.clone()
    my_pol = my_policy or passive_policy
    opp_pol = opp_policy or charge_only_policy
    start = own_turn(e, me)
    run = LockRun(set_turn=start)
    base, last = None, None
    while (d := e.advance()) is not None:
        if e.s.active == me and e.s.turn != last:
            last = e.s.turn
            if own_turn(e, me) - start > max_turns:
                run.broken, run.broken_turn = f"{max_turns} ターン以内に終わらない", own_turn(e, me)
                break
            now = opp_resources(e, me)
            if own_turn(e, me) == start:      # 成立したターンはまだ一巡していない。基準は次の自分のターン開始
                pass
            elif base is None:
                base = now
            else:
                grow = {k: v - base.get(k, 0) for k, v in now.items() if v - base.get(k, 0) > slack}
                if grow:
                    run.broken, run.opp_growth = "相手の資源が増えた: " + ", ".join(f"{k} +{v}" for k, v in grow.items()), grow
                    run.broken_turn = own_turn(e, me)
                    break
        e.answer(my_pol(e, d) if d["player"] == me else opp_pol(e, d))
    r = e.s.result
    run.result = r
    run.own_deck_left = len(e.zlist("deck", me))
    if r is not None:
        if r["winner"] == me and r["reason"] == "deck_out":
            run.won = True
            run.win_turn = own_turn(e, me, r["turn"])
            run.turns_to_win = run.win_turn - start
        elif run.broken is None:
            run.broken = f"自分が先に尽きた（{r['reason']}）" if r["winner"] != me and r["reason"] == "deck_out" \
                else f"終局 winner={r['winner']} reason={r['reason']}"
    elif run.broken is None:
        run.broken = "終局しないまま決定が尽きた"
    return run


def make_full_lock_judge(*, my_policy: Policy | None = None, max_turns: int = 80):
    """play_game の lock_judge に差し込める判定役。lock_probe でロックを見つけ、さらに run_lock_to_end で
    相手の山札切れまで回して勝てたものだけを返す（cert.notes に結果を書く）。play_game の既定にはまだしていない。"""
    def judge(eng: Engine, me: int, rounds: int) -> LoopCertificate | None:
        cert = lock_probe(eng, me, rounds)
        if cert is None:
            return None
        run = run_lock_to_end(eng, me, my_policy=my_policy, max_turns=max_turns)
        cert.notes.append(f"lock_run: won={run.won} turns_to_win={run.turns_to_win} "
                          f"own_deck_left={run.own_deck_left} broken={run.broken}")
        return cert if run.won else None
    return judge


_lock_ok = lock_ok    # 旧名（互換）

set_default_lock_judge(lock_probe)
