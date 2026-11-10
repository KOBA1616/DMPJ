from pathlib import Path

from dmsim.defs import load_rules
from dmsim.engine.core import Engine
from dmsim.eval.vfeatures import Plan, v_priority
from dmsim.plan.macro import MacroPlanner, load_stage_file, stage_fraction

STAGES = [{"hand": {"*": 1}}, {"hand": {"*": 5}}, {"shield": {"*": 99}}]


def _eng():
    return Engine.new_game(load_rules(), [["T001"] * 40, ["T001"] * 40], 1, first_player=0)


def test_plan_picks_first_unmet_stage():
    p = MacroPlanner(STAGES).plan(_eng(), 0)
    assert isinstance(p, Plan) and p.idx == 2 and p.intent == "execute" and p.budget > 0


def test_progress_and_fraction():
    e = _eng()
    pl = MacroPlanner(STAGES).plan(e, 0)
    assert 2.0 <= stage_fraction(e, 0, pl) < 3.0
    assert v_priority(e, 0, None, lambda *a: 0.0, plan=pl, plan_w=10.0) > v_priority(e, 0, None, lambda *a: 0.0, plan=pl)


def test_tenmon_stage_file():
    stages, goal = load_stage_file(Path("data/eval/stages/tenmon.yaml"))
    assert len(stages) == 10 and goal
    assert MacroPlanner(stages).plan(_eng(), 0).intent == "setup"
