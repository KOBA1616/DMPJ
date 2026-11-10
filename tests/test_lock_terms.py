from dmsim.defs import load_rules
from dmsim.engine.core import Engine
from dmsim.eval.lock_terms import classify_static, lock_term, static_counts
from dmsim.eval.vfeatures import v_priority


def test_classify_static():
    tax = {"kind": "static", "affects": {"owner": "opp", "zone": "hand"}, "mod": {"cost": 2}}
    assert classify_static(tax) == "lock"
    assert classify_static({"kind": "static", "affects": "self", "mod": {"breaks": 2}}) is None
    assert classify_static({"kind": "static", "affects": {"owner": "you"}, "mod": {"grant": ["speed_attacker"]}}) == "buff"
    assert classify_static({"kind": "trigger"}) is None


def test_term_zero_on_empty_board_and_pluggable():
    e = Engine.new_game(load_rules(), [["T001"] * 40, ["T001"] * 40], 1, first_player=0)
    assert static_counts(e, 0) == {"lock": 0, "buff": 0}
    assert lock_term(e, 0) == 0.0
    assert v_priority(e, 0, None, lambda *a: 1.0, under_w=0, res_w=0, terms=[lambda eng, me: lock_term(eng, me)]) == 1.0
