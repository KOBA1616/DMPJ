from dmsim import scenario
from dmsim.engine_view import active_of, defn_of, defns_of, digest_of, result_of, tapped_of, turn_of, zone_of


def test_view_matches_state(rules):
    e = scenario.build(rules, {"p0": {"hand": ["T001", "T001"], "mana": ["T001"]}, "p1": {}, "seed": 1, "deck_size": 10})
    e.advance()
    assert result_of(e) is e.s.result and active_of(e) == e.s.active and turn_of(e) == e.s.turn
    assert zone_of(e, "hand", 0) == e.s.zones["hand"][0]
    assert defns_of(e, "hand", 0) == ["T001", "T001"] and defn_of(e, zone_of(e, "hand", 0)[0]) == "T001"
    assert tapped_of(e, zone_of(e, "mana", 0)[0]) is False and digest_of(e) == e.s.digest()
