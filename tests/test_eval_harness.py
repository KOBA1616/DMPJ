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


def test_fair_unregistered_raises():
    from dmsim.eval import infolevel
    infolevel._RUNNERS.pop(InfoLevel.FAIR, None)
    with pytest.raises(NotImplementedError):
        get_runner(InfoLevel.FAIR)


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
