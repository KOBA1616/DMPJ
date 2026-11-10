from dmsim.defs import load_rules
from dmsim.engine.core import Engine
from dmsim.eval.key_terms import key_in_mana_penalty, make_term, stage_ids


def test_stage_ids_and_penalty():
    stages = [{"hand": {"a": 1, "b": 1}}, {"shield": {"*": 8}}, {"bz": {"c": 1}}]
    assert stage_ids(stages) == {"a", "b", "c"}
    e = Engine.new_game(load_rules(), [["T001"] * 40, ["T001"] * 40], 1, first_player=0)
    assert key_in_mana_penalty(e, 0, {"T001"}) == 0.0          # マナはまだ空
    assert make_term(stages)(e, 0) == 0.0
