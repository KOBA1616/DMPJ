"""ロック判定（S4 構造検証、P2 タスク2 で dmsim.search.game から移動）。
round_probe: 自分が何もしなくなってもラウンド周期で骨格が戻るかの試し回し。lock_probe: それが相手を山札切れへ追うロックか。
S3 の play_game は判定役を引数 lock_judge で受け取り、省略時はここで登録する lock_probe を使う。
"""
from __future__ import annotations

from ..engine import Engine
from ..engine.loop import LoopCertificate, LoopDetector, verify
from ..engine.play import passive_policy
from ..search.game import set_default_lock_judge
from ..search.turn import charge_only_policy


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


_lock_ok = lock_ok    # 旧名（互換）

set_default_lock_judge(lock_probe)
