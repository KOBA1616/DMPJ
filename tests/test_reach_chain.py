from dmsim.defs import load_rules
from dmsim.engine.core import Engine
from dmsim.discovery.reachsearch import reach_chain


def test_chain_stops_at_unreachable_stage():
    rules = load_rules()
    e = Engine.new_game(rules, [["T001"] * 40, ["T001"] * 40], 1, first_player=0)
    r = reach_chain(e, [{"hand": {"*": 1}}, {"shield": {"*": 99}}], width=5, max_depth=3, max_turn=2)
    assert r["stages"] == 1 and len(r["turns"]) == 1
