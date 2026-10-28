"""最良優先探索（dmsim/discovery/bestfirst.py）が、簡単な盤面で常在の勝利条件までたどり着く。"""
from dmsim import load_rules, scenario
from dmsim.discovery import bestfirst

AL, EM, HG = "dmx12b-031", "dm23bd7-022", "dm16-007"


def test_bestfirst_reaches_state_win_with_one_shield_to_add():
    rules = load_rules()
    spec = {"p0": {"hand": [EM, "T013"], "bz": [AL], "mana": [HG] * 5, "shield": ["T013"] * 9}, "p1": {"bz": ["T001"]},
            "filler": "T013", "seed": 1, "deck_size": 10}
    e = scenario.build(rules, spec)
    r = bestfirst.search(e, 0, 3000)
    assert r.won and r.engine.s.result["reason"] == "state" and len(r.engine.zlist("shield", 0)) == 10


def test_beam_wins_the_tenmon_loop_from_the_middle_of_the_walk():
    """天門(初期型)の手動手順の途中(待機を積み始めたところ)から、ビーム探索が自力で盾10枚の勝ちを見つける。"""
    import contextlib
    import io
    from pathlib import Path
    ns = {"STOP": 16, "__name__": "tenmon_walk"}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile((Path(__file__).parent.parent / "tools" / "tenmon_walk.py").read_text(), "tenmon_walk.py", "exec"), ns)
    r = bestfirst.beam(ns["e"], 0, width=100)
    assert r.won and r.engine.s.result["reason"] == "state" and len(r.engine.zlist("shield", 0)) == 10
