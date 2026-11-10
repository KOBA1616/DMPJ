"""相手の資源（マナ・山札・盾）の減少を加点する評価項。v_priority の `terms` に渡す (eng, me) -> 加点 の関数。
山札は見えない公平探索でも枚数は見える（公開情報）ので使ってよい。足切りには使わず順位づけのみ。"""
from __future__ import annotations


def _n(eng, zone: str, p: int) -> int:
    return len(eng.zlist(zone, p))


def opp_pressure(eng, me: int, mana_w: float = 1.0, deck_w: float = 0.3, shield_w: float = 1.0,
                 mana0: int = 6, deck0: int = 30, shield0: int = 5) -> float:
    """相手の減少量 = 初期値からの不足分 × 係数。初期値は標準開始局面の目安。"""
    o = 1 - me
    return (mana_w * max(0, mana0 - _n(eng, "mana", o))
            + deck_w * max(0, deck0 - _n(eng, "deck", o))
            + shield_w * max(0, shield0 - _n(eng, "shield", o)))


def make_term(**kw):
    return lambda eng, me: opp_pressure(eng, me, **kw)
