"""評価関数 V の特徴量と、計画つきの順位づけ（docs/value-function-design.md）。
v_priority は bestfirst.priority に「盾の束」「資源の総量」を足したもの。足切りには使わない（順位づけの補助）。"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..engine_view import zone_of


@dataclass
class Plan:
    """大局観などが出す計画（版つき・どの出し手でも同じ形）。stages は reach_target 形式の目標の列、idx は現在狙う段。"""
    intent: str = ""
    stages: list = field(default_factory=list)
    idx: int = 0
    version: int = 1
    budget: int = 0     # 探索の幅などの目安（0 は指定なし）

    @property
    def current(self) -> dict | None:
        return self.stages[self.idx] if 0 <= self.idx < len(self.stages) else None


def shield_bundle(eng, me: int) -> tuple[int, int, int]:
    """(盾の下の合計枚数, 最大の束の枚数, 束のある盾の数)。"""
    n = [len(eng.s.cards[c].under) for c in eng.zlist("shield", me)]
    return sum(n), max(n, default=0), sum(1 for x in n if x)


def resource_total(eng, me: int) -> int:
    """見える資源の総量: 手札 + 盾 + 盾の下 + 場の札。"""
    under = shield_bundle(eng, me)[0]
    return len(eng.zlist("hand", me)) + len(eng.zlist("shield", me)) + under + len(zone_of(eng, "bz", me))


def v_priority(eng, me: int, w, base, under_w: float = 3.0, res_w: float = 1.0, plan: Plan | None = None,
               plan_w: float = 0.0) -> float:
    """base は bestfirst.priority。盾の束と資源総量を足す（係数 0 なら base と同じ）。"""
    v = base(eng, me, w)
    if under_w:
        v += under_w * shield_bundle(eng, me)[0]
    if res_w:
        v += res_w * resource_total(eng, me)
    if plan is not None and plan_w and plan.stages:
        from ..plan.macro import stage_fraction   # 循環を避けるため遅延 import
        v += plan_w * stage_fraction(eng, me, plan)
    return v
