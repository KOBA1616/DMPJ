"""評価関数 V の特徴量と、計画つきの順位づけ（docs/value-function-design.md）。
v_priority は bestfirst.priority に「盾の束」「資源の総量」を足したもの。足切りには使わない（順位づけの補助）。"""
from __future__ import annotations

from ..engine_view import zone_of
from ..plan.macro import Plan, RunStd, MacroPlanner, stage_fraction  # noqa: F401  Plan は旧名の再公開（実体は plan.macro）


def shield_bundle(eng, me: int) -> tuple[int, int, int]:
    """(盾の下の合計枚数, 最大の束の枚数, 束のある盾の数)。"""
    n = [len(eng.s.cards[c].under) for c in eng.zlist("shield", me)]
    return sum(n), max(n, default=0), sum(1 for x in n if x)


def resource_total(eng, me: int) -> int:
    """見える資源の総量: 手札 + 盾 + 盾の下 + 場の札。"""
    under = shield_bundle(eng, me)[0]
    return len(eng.zlist("hand", me)) + len(eng.zlist("shield", me)) + under + len(zone_of(eng, "bz", me))


def v_priority(eng, me: int, w, base, under_w: float = 3.0, res_w: float = 1.0, plan: Plan | None = None,
               plan_w: float = 0.0, terms=()) -> float:
    """base は bestfirst.priority。盾の束と資源総量を足す（係数 0 なら base と同じ）。"""
    v = base(eng, me, w)
    if under_w:
        v += under_w * shield_bundle(eng, me)[0]
    if res_w:
        v += res_w * resource_total(eng, me)
    if plan is not None and plan_w and plan.stages:
        v += plan_w * stage_fraction(eng, me, plan)
    for t in terms:   # 追加項（別ファイルで定義した (eng, me) -> 加点 の関数。例: 相手の資源減少の項）
        v += t(eng, me)
    return v


def macro_prio(stages: list, plan_w: float, under_w: float = 3.0, res_w: float = 1.0, base=None, terms=()):
    """reach_chain/reach_target の prio に渡せる順位づけ。局面ごとに MacroPlanner が現在の段を決め直し、V の計画項に使う
    （段をまたぐ鎖でも1つの関数で済む）。plan_w=0 は計画なしと同じ。
    plan_w<0 は「基本スコアの標準偏差に対する倍率 k=-plan_w」（正規化。局面ごとの散らばりに計画項の大きさを合わせる）。"""
    from ..search.bestfirst import priority
    planner = MacroPlanner(stages)
    b = base or priority
    rs = RunStd() if plan_w < 0 else None

    def prio(eng, me, w):
        if rs is None:
            return v_priority(eng, me, w, b, under_w=under_w, res_w=res_w, plan=planner.plan(eng, me), plan_w=plan_w, terms=terms)
        v0 = v_priority(eng, me, w, b, under_w=under_w, res_w=res_w, terms=terms)
        rs.add(v0)
        return v0 + (-plan_w) * rs.std * stage_fraction(eng, me, planner.plan(eng, me))
    return prio
