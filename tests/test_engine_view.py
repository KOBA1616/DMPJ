from dmsim import scenario
from dmsim.engine_view import active_of, defn_of, defns_of, digest_of, result_of, tapped_of, turn_of, zone_of


def test_view_matches_state(rules):
    e = scenario.build(rules, {"p0": {"hand": ["T001", "T001"], "mana": ["T001"]}, "p1": {}, "seed": 1, "deck_size": 10})
    e.advance()
    assert result_of(e) is e.s.result and active_of(e) == e.s.active and turn_of(e) == e.s.turn
    assert zone_of(e, "hand", 0) == e.s.zones["hand"][0]
    assert defns_of(e, "hand", 0) == ["T001", "T001"] and defn_of(e, zone_of(e, "hand", 0)[0]) == "T001"
    assert tapped_of(e, zone_of(e, "mana", 0)[0]) is False and digest_of(e) == e.s.digest()


def test_write_ops(rules):
    import random
    from dmsim.engine_view import inject_state, order_zone, shuffle_deck, state_of, trace_of, trace_on
    mk = lambda: scenario.build(rules, {"p0": {"hand": ["T001"]}, "p1": {}, "seed": 1, "deck_size": 12})
    a, b = mk(), mk()
    shuffle_deck(a, 0, random.Random(5))
    ref = list(b.s.zones["deck"][0]); random.Random(5).shuffle(ref)
    assert zone_of(a, "deck", 0) == ref                       # 直接 shuffle した結果と同一
    order_zone(a, "deck", 0, lambda c: -c)
    assert list(zone_of(a, "deck", 0)) == sorted(ref, reverse=True)
    c = mk(); inject_state(c, state_of(b)); assert c.s is b.s
    trace_on(c); assert trace_of(c) == []
