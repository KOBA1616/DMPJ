"""大局観（MacroPlanner）: 局面と段階目標の鎖から、いま狙う段と探索の動かし方を Plan として出す。
Plan の形は dmsim.eval.vfeatures.Plan（V と共通）。自分側の見える情報だけを使う（公平探索）。
段階目標は reach_target の形 {ゾーン: {ID or "*": 枚数}}。段階は途中で崩れうる（手札の札を使う等）ので、
最初の未達の段を狙う。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..discovery.reachsearch import board_met, fraction
from ..eval.vfeatures import Plan

BASE_BUDGET = 150          # reach_target の幅の基準
PLAN_VERSION = 1
NEXT_W = 0.0               # 次の段の充足率を先読みで足す重み。0.5 だと今の段を終える前に次の段へ寄って天門で逆効果(2026-11-10)


def load_stage_file(path) -> tuple[list[dict], dict]:
    """data/eval/stages/*.yaml → (段階目標の列, 勝利条件)。"""
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [s["target"] for s in d["stages"]], d.get("goal", {})


def load_stage_graph(path):
    """data/eval/stages/*.yaml → (StageGraph, 勝利条件)。id / requires が無いファイルは従来の鎖として読む。"""
    from .stagegraph import StageGraph
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return StageGraph.from_stage_dicts(d["stages"]), d.get("goal", {})


@dataclass
class MacroPlanner:
    """規則ベース v1（共通）: 段階の鎖のうち未達の最初の段を現在の狙いにする。
    intent: setup（最初の段へ）/ chain（中間の段）/ execute（最後の段）/ done。
    budget: 残り段数に比例して探索の幅を増やす（遠いほど広く探す）。"""
    stages: list = field(default_factory=list)    # 目標の列、または StageGraph（前提つき。並列・選択肢の段を含んでもよい）
    base_budget: int = BASE_BUDGET

    def __post_init__(self):
        from .stagegraph import StageGraph
        self.graph = None
        if isinstance(self.stages, StageGraph):
            self.graph = None if self.stages.is_chain() else self.stages
            self.stages = self.stages.targets()

    def _graph_state(self, eng, me: int):
        """(済んだ段の列, 今狙える段の列)。段は、局面で満たされていて前提も済んでいれば済み。"""
        sat, done = [], set()
        for n in self.graph.nodes:
            if self.graph.req_met(n, done) and board_met(eng, me, n.target):
                sat.append(n)
                done.add(n.id)
        return sat, [n for n in self.graph.nodes if n.id not in done and self.graph.req_met(n, done)]

    def progress(self, eng, me: int = 0) -> int:
        """最初の未達の段の番号（全段達成で len(stages)）。後ろの段が先に満たされても、手前が未達なら手前を狙う。
        以前の「満たされた最後の段の次」は、手前の段の盤面を崩すと番号が下がって減点になり、天門で段を進められなくなった(2026-11-10)。"""
        if self.graph is not None:
            return len(self._graph_state(eng, me)[0])
        for i, tg in enumerate(self.stages):
            if not board_met(eng, me, tg):
                return i
        return len(self.stages)

    def plan(self, eng, me: int = 0) -> Plan:
        if self.graph is not None:
            return self._plan_graph(eng, me)
        n = len(self.stages)
        idx = self.progress(eng, me)
        if idx >= n:
            intent = "done"
        elif idx == 0:
            intent = "setup"
        elif idx == n - 1:
            intent = "execute"
        else:
            intent = "chain"
        remain = max(0, n - idx)
        return Plan(intent=intent, stages=list(self.stages), idx=idx, version=PLAN_VERSION,
                    budget=self.base_budget * (1 + remain // 4))

    def _plan_graph(self, eng, me: int) -> Plan:
        """前提つきの段の集合: 済んだ段 → 今狙える段のうち充足率が最大の段 → 残り（前提の順）に並べ替えて、Plan（鎖の形）で返す。"""
        sat, ready = self._graph_state(eng, me)
        n = len(self.graph.nodes)
        done_ids = {x.id for x in sat}
        cur = max(ready, key=lambda x: fraction(eng, me, x.target)) if ready else None
        rest = [x for x in self.graph.nodes if x.id not in done_ids and (cur is None or x.id != cur.id)]
        order = sat + ([cur] if cur else []) + rest
        idx = len(sat)
        intent = "done" if idx >= n else "setup" if idx == 0 else "execute" if idx == n - 1 else "chain"
        remain = max(0, n - idx)
        return Plan(intent=intent, stages=[x.target for x in order], idx=idx, version=PLAN_VERSION,
                    budget=self.base_budget * (1 + remain // 4))


def stage_fraction(eng, me: int, plan: Plan) -> float:
    """計画上の進み具合: 達成段数 + 現在の段の充足率（0〜len(stages)）。V の期待状態項に使う。"""
    cur = plan.current
    if cur is None:
        return float(len(plan.stages))
    nxt = plan.stages[plan.idx + 1] if plan.idx + 1 < len(plan.stages) else None
    return plan.idx + fraction(eng, me, cur) + (NEXT_W * fraction(eng, me, nxt) if nxt else 0.0)


class RunStd:
    """基本スコアの標準偏差を探索中にオンラインで推定する（Welford）。計画項の大きさを基本スコアの散らばりに合わせる。"""

    def __init__(self, floor: float = 1.0, warm: int = 30):
        self.n, self.mean, self.m2, self.floor, self.warm = 0, 0.0, 0.0, floor, warm

    def add(self, x: float) -> None:
        self.n += 1
        d = x - self.mean
        self.mean += d / self.n
        self.m2 += d * (x - self.mean)

    @property
    def std(self) -> float:
        if self.n < self.warm:
            return self.floor
        return max(self.floor, (self.m2 / (self.n - 1)) ** 0.5)


def macro_prio(stages: list, plan_w: float, under_w: float = 3.0, res_w: float = 1.0, base=None, terms=()):
    """reach_chain/reach_target の prio に渡せる順位づけ。局面ごとに MacroPlanner が現在の段を決め直し、V の計画項に使う
    （段をまたぐ鎖でも1つの関数で済む）。plan_w=0 は計画なしと同じ。
    plan_w<0 は「基本スコアの標準偏差に対する倍率 k=-plan_w」（正規化。局面ごとの散らばりに計画項の大きさを合わせる）。"""
    from ..discovery.bestfirst import priority
    from ..eval.vfeatures import v_priority
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
