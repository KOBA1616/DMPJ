from dmsim.cards.defs import load_rules
from dmsim.engine.core import Engine
from dmsim.eval.vfeatures import Plan, resource_total, shield_bundle, v_priority


def test_features_and_plan():
    e = Engine.new_game(load_rules(), [["T001"] * 40, ["T001"] * 40], 1, first_player=0)
    assert shield_bundle(e, 0) == (0, 0, 0)
    assert resource_total(e, 0) == 10   # 手札5 + 盾5
    assert v_priority(e, 0, None, lambda *a: 0.0, under_w=0, res_w=2.0) == 20.0
    p = Plan(stages=[{"hand": {"*": 1}}, {"shield": {"*": 8}}])
    assert p.current == {"hand": {"*": 1}}
    p.idx = 9
    assert p.current is None


def test_extra_terms_are_added():
    e = Engine.new_game(load_rules(), [["T001"] * 40, ["T001"] * 40], 1, first_player=0)
    base = lambda *a: 1.0
    assert v_priority(e, 0, None, base, under_w=0, res_w=0, terms=[lambda eng, me: 5.0, lambda eng, me: 2.0]) == 8.0
