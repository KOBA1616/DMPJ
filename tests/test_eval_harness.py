import pytest

from dmsim.eval import explog
from dmsim.eval.harness import EvalConfig, compare, hidden_info_cost, run_eval
from dmsim.eval.infolevel import InfoLevel, get_runner, register_runner
from dmsim.eval.stats import boot_ci, paired_diff
from dmsim.solitaire import GameResult


def _fake(kill_by_seed):
    def run(rules, deck, opp, seed, fp, max_turn, budget):
        return GameResult(seed=seed, first_player=fp, kill_turn=kill_by_seed(seed), nodes=budget)
    return run


def test_fair_default_registered():
    from dmsim.eval import infolevel
    infolevel._RUNNERS.pop(InfoLevel.FAIR, None)
    assert callable(get_runner(InfoLevel.FAIR))  # 既定で FairTurnSearch が登録される


def test_harness_cells_and_hidden_cost():
    register_runner(InfoLevel.CHEAT, _fake(lambda s: 3))
    register_runner(InfoLevel.FAIR, _fake(lambda s: 3 if s % 2 else None))
    cfg = EvalConfig(decks={"d": ["x"]}, opp_deck=["y"], seeds=list(range(1, 21)), budget_mults=(0.5, 1.0), first="first",
                     known_combos={"c": lambda r: r.kill_turn == 3})
    rep = run_eval(None, cfg)
    assert set(rep["cells"]) == {f"d|{l}|x{m}" for l in ("fair", "cheat") for m in (0.5, 1.0)}
    assert rep["cells"]["d|cheat|x1.0"]["kill_rate_by_turn"][3]["rate"] == 1.0
    assert rep["cells"]["d|fair|x0.5"]["mean_nodes"] == 100
    cost = hidden_info_cost(rep, "d", 3)
    assert cost["diff"] == pytest.approx(0.5) and cost["significant"]
    same = compare(rep, rep, "d|fair|x1.0", 3)
    assert not same["significant"]


def test_paired_and_ci():
    m, lo, hi = boot_ci([1.0] * 10)
    assert m == lo == hi == 1.0
    with pytest.raises(ValueError):
        paired_diff([1], [1, 2])


def test_explog_version(tmp_path):
    p = tmp_path / "l.jsonl"
    with explog.LogWriter(p, {"a": 1}, engine_ver="v1") as w:
        w.step(state="s", legal=["a"], chosen="a", policy_id="p", opp_id="o", seed=1, turn=1, result=None)
        with pytest.raises(ValueError):
            w.step(state="s")
    h, steps = explog.read_log(p, "v1")
    assert len(steps) == 1 and h["engine_version"] == "v1"
    with pytest.raises(explog.VersionMismatch):
        explog.read_log(p, "v2")
    assert explog.summarize_log(p)["steps"] == 1


def test_opp_axis_and_keys():
    seen = []

    def run(rules, deck, opp_deck, seed, fp, max_turn, budget, **kw):
        seen.append(kw.get("opp"))
        return GameResult(seed=seed, first_player=fp, kill_turn=3 if (kw.get("opp") is None or seed % 2) else None)

    register_runner(InfoLevel.CHEAT, run)
    register_runner(InfoLevel.FAIR, run)
    from dmsim.opponent import PRESETS
    cfg = EvalConfig(decks={"d": ["x"]}, opp_deck=["y"], seeds=list(range(1, 5)), first="first",
                     opps={"none": None, "blockers": PRESETS["blockers"]})
    rep = run_eval(None, cfg)
    assert "d|fair|x1.0" in rep["cells"] and "d|fair|x1.0|opp=blockers" in rep["cells"]
    assert rep["cells"]["d|fair|x1.0|opp=blockers"]["kill_rate_by_turn"][3]["rate"] == 0.5
    assert PRESETS["blockers"] in seen and None in seen
    assert hidden_info_cost(rep, "d", 3, opp="blockers")["diff"] == 0.0


def test_fair_runner_accepts_opp():
    import inspect
    from dmsim.eval.fair_runner import make_fair_runner
    assert "opp" in inspect.signature(make_fair_runner()).parameters


def test_progress_metrics_real_engine():
    """実エンジンで段階指標が記録され、harness 集計と対比較に流れる（サガのキル手前の局面）。"""
    import yaml
    from pathlib import Path
    from dmsim.defs import load_rules
    from dmsim.eval.harness import hidden_info_cost_progress
    from dmsim.eval.progress import ProgressSpec
    spec = yaml.safe_load(Path("tests/saga_setup.yaml").read_text(encoding="utf-8"))
    cfg = EvalConfig(decks={"d": ["T001"] * 40}, opp_deck=["T001"] * 40, seeds=[1, 2], first="first", base_budget=10, max_turn=1,
                     n_det=2, start_spec=spec, progress=ProgressSpec(board={"graveyard": {"dm22ex2-021": 1}}, cards={"dm22ex2-021": 1}))
    rep = run_eval(load_rules(), cfg)
    c = rep["cells"]["d|fair|x1.0"]["progress"]
    assert c["board_turn"]["reach_rate"] == 1.0 and c["cards_turn"]["reach_rate"] == 1.0
    assert set(c["curve_mean"]) == {0, 1}
    assert hidden_info_cost_progress(rep, "d", "opp_shield")["n"] == 2


def test_calibrate_mult_converges():
    from dmsim.eval.harness import calibrate_mult
    f = lambda m: 100.0 * m ** 0.5           # 非線形（早期終了で予算に比例しない）
    m, got = calibrate_mult(f, 400.0, 1.0, 0.05, 6)
    assert abs(got - 400.0) <= 0.05 * 400.0 and 15 < m < 17


def test_match_nodes_in_run_eval():
    fair = lambda rules, deck, o, seed, fp, mt, budget, **kw: GameResult(seed=seed, first_player=fp, kill_turn=None, nodes=500)
    cheat = lambda rules, deck, o, seed, fp, mt, budget, **kw: GameResult(seed=seed, first_player=fp, kill_turn=None, nodes=budget * 2)
    register_runner(InfoLevel.FAIR, fair)
    register_runner(InfoLevel.CHEAT, cheat)
    cfg = EvalConfig(decks={"d": ["x"]}, opp_deck=["y"], seeds=[1, 2, 3], first="first", base_budget=100, match_nodes=True)
    rep = run_eval(None, cfg)
    c = rep["cells"]["d|cheat|x1.0"]
    assert abs(c["mean_nodes"] - 500) <= 50 and abs(c["budget_mult_used"] - 2.5) < 0.3
