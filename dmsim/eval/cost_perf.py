"""コスト対総合パフォーマンスの項（docs/value-function-design.md §4）。v_priority の `terms` に渡す (eng, me) -> 加点 の関数。足切りには使わず順位づけのみ。
- 分母: 使用マナ（今ターンにタップしたマナ）+ 1。マナ0の手は小さな分母のまま、手札・場の札の消費はマナ換算で加える（hand_cost_w）。
- 分子: 現象の種類別の和（内訳ベクトル breakdown と重み付き合計の両方を出す）。
  資源（手札・盾・マナ・墓地）、盤面（場の数）、妨害（相手の資源減少 = opp_pressure）、ロック（継続効果 = lock_terms）。
- 項 = scale × 分子 / 分母。scale は基本スコアの散らばりに合わせるため呼び出し側で決める（tools/plan_effect.py --term cost）。"""
from __future__ import annotations

from ..engine.view import tapped_of, zone_of
from .lock_terms import lock_term
from .opp_pressure import opp_pressure

W = {"hand": 5.0, "shield": 10.0, "mana": 8.0, "grave": 3.0, "board": 15.0, "disrupt": 1.0, "lock": 1.0}


def breakdown(eng, me: int) -> dict:
    """現象別の内訳（重みを掛ける前の値）。"""
    return {
        "hand": len(zone_of(eng, "hand", me)),
        "shield": len(zone_of(eng, "shield", me)),
        "mana": len(zone_of(eng, "mana", me)),
        "grave": len(zone_of(eng, "graveyard", me)),
        "board": len(eng.bz_tops(me)),
        "disrupt": opp_pressure(eng, me) / 100.0,
        "lock": lock_term(eng, me) / 100.0,
    }


def performance(eng, me: int, w: dict | None = None) -> float:
    w = w or W
    b = breakdown(eng, me)
    return sum(w[k] * v for k, v in b.items())


def mana_used(eng, me: int) -> int:
    return sum(1 for c in zone_of(eng, "mana", me) if tapped_of(eng, c))


NET_W = 2.0   # 差型（scale<0）での使用マナ1あたりの減点


def cost_perf(eng, me: int, scale: float = 1.0, hand_cost_w: float = 0.0, w: dict | None = None) -> float:
    """scale>0: 割り算型 性能/(1+使用マナ)。性能がほぼ一定の局面では、使用マナ0（何もしない）が最良になり行動を罰する
    （天門で 使用マナ0=132、3〜6=18〜36。V gate は 38→26 と悪化）。
    scale<0: 差型 |scale|×(性能 − NET_W×使用マナ)。行動を罰する度合いが使用マナに比例するだけで済む。"""
    used = mana_used(eng, me)
    hand_cost = hand_cost_w * max(0, 5 - len(zone_of(eng, "hand", me)))
    if scale < 0:
        return -scale * (performance(eng, me, w) - NET_W * (used + hand_cost))
    return scale * performance(eng, me, w) / (1 + used + hand_cost)


def make_term(**kw):
    return lambda eng, me: cost_perf(eng, me, **kw)
