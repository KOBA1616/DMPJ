"""大局観（MacroPlanner）: 局面と段階目標の鎖から、いま狙う段と探索の動かし方を Plan として出す。
Plan の形は dmsim.eval.vfeatures.Plan（V と共通）。自分側の見える情報だけを使う（公平探索）。
段階目標は reach_target の形 {ゾーン: {ID or "*": 枚数}}。段階は途中で崩れうる（手札の札を使う等）ので、
満たしている最後の段の次を狙う（途中が崩れていても後ろの段が満たされていれば前進とみなす）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..discovery.reachsearch import board_met, fraction
from ..eval.vfeatures import Plan

BASE_BUDGET = 150          # reach_target の幅の基準
PLAN_VERSION = 1
NEXT_W = 0.5               # 次の段の充足率を先読みで足す重み


def load_stage_file(path) -> tuple[list[dict], dict]:
    """data/eval/stages/*.yaml → (段階目標の列, 勝利条件)。"""
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [s["target"] for s in d["stages"]], d.get("goal", {})


@dataclass
class MacroPlanner:
    """規則ベース v1（共通）: 段階の鎖のうち未達の最初の段を現在の狙いにする。
    intent: setup（最初の段へ）/ chain（中間の段）/ execute（最後の段）/ done。
    budget: 残り段数に比例して探索の幅を増やす（遠いほど広く探す）。"""
    stages: list = field(default_factory=list)
    base_budget: int = BASE_BUDGET

    def progress(self, eng, me: int = 0) -> int:
        """満たされている最後の段の次の番号（全段達成で len(stages)）。"""
        last = -1
        for i, tg in enumerate(self.stages):
            if board_met(eng, me, tg):
                last = i
        return last + 1

    def plan(self, eng, me: int = 0) -> Plan:
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


def stage_fraction(eng, me: int, plan: Plan) -> float:
    """計画上の進み具合: 達成段数 + 現在の段の充足率（0〜len(stages)）。V の期待状態項に使う。"""
    cur = plan.current
    if cur is None:
        return float(len(plan.stages))
    nxt = plan.stages[plan.idx + 1] if plan.idx + 1 < len(plan.stages) else None
    return plan.idx + fraction(eng, me, cur) + (NEXT_W * fraction(eng, me, nxt) if nxt else 0.0)
