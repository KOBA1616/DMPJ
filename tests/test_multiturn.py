from dmsim import scenario
from dmsim.search import FairTurnSearch
from dmsim.search.multiturn import advance_to_own_turn, make_lookahead_value_fn
from dmsim.solitaire import Weights, charge_only_policy, evaluate


def _eng(rules):
    e = scenario.build(rules, {"p0": {"hand": ["T001", "T073"], "mana": ["T004"] * 4}, "p1": {}, "filler": "T001",
                               "seed": 1, "deck_size": 20, "deck_left": None})
    e.advance()
    return e


def test_advance_to_own_turn_reaches_next_turn(rules):
    e = _eng(rules)
    t = e.s.turn
    out = FairTurnSearch(0, budget=20, n_det=2, seed=1).run(e)      # 自分のターンを終えた局面（相手の番）
    assert out.s.active != 0
    assert advance_to_own_turn(out, 0, charge_only_policy)
    assert out.s.active == 0 and out.s.turn > t


def test_lookahead_value_not_below_base_and_input_untouched(rules):
    e = _eng(rules)
    fs = FairTurnSearch(0, budget=20, n_det=2, seed=1)
    out = fs.run(e)                                                  # 自分のターン終了後の局面
    n = len(out.log)
    f = make_lookahead_value_fn(None, 10)
    assert f(out, 0) >= evaluate(out, 0, Weights())
    assert len(out.log) == n


def test_fair_turn_search_with_lookahead_runs_and_is_deterministic(rules):
    e = _eng(rules)
    a = FairTurnSearch(0, budget=20, n_det=2, seed=3, lookahead=8).run(e)
    b = FairTurnSearch(0, budget=20, n_det=2, seed=3, lookahead=8).run(e)
    assert a.log == b.log
