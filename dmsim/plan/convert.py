"""既存の LoopSpec と PlanSpec の変換。"""
from __future__ import annotations

from dmsim.base.loopspec import LoopSpec
from .spec import PlanSpec


def from_loopspec(ls: LoopSpec, roles: tuple[str, ...] = ("win_path",)) -> PlanSpec:
    return PlanSpec(
        kind="loop", roles=roles, minimal=list(ls.minimal), routes=list(ls.routes), goal=list(ls.goal),
        hazards=list(ls.hazards), source=dict(ls.source),
        params={"name": ls.name, "loop_kind": ls.kind, "delta": dict(ls.delta),
                "limit": ls.limit, "deck_floor": ls.deck_floor},
    )


def to_loopspec(ps: PlanSpec) -> LoopSpec:
    if ps.kind != "loop":
        raise ValueError("loop 以外は LoopSpec にできない")
    p = ps.params
    return LoopSpec(
        name=p["name"], kind=p["loop_kind"], minimal=list(ps.minimal), delta=dict(p.get("delta", {})),
        limit=p.get("limit"), goal=list(ps.goal), deck_floor=p.get("deck_floor", 1),
        hazards=list(ps.hazards), routes=list(ps.routes), source=dict(ps.source),
    )
