from dmsim import scenario
from dmsim.search import determinize, hidden_cids


def _state(rules, deck_order):
    e = scenario.build(rules, {"p0": {}, "p1": {}, "filler": "T001", "seed": 1, "deck_size": 20, "deck_left": None})
    return e.s


def test_multiset_preserved_and_visible_fixed(rules):
    s = _state(rules, None)
    d = determinize(s, 0, seed=5)
    hid = hidden_cids(s, 0)
    for owner in (0, 1):
        assert sorted(s.cards[c].defn for c in hid[owner]) == sorted(d.cards[c].defn for c in hid[owner])
    hidset = {c for v in hid.values() for c in v}
    for c in s.cards:
        if c.cid not in hidset:
            assert d.cards[c.cid].defn == c.defn
    assert s.cards is not d.cards


def test_own_hand_visible_opp_hand_hidden(rules):
    s = _state(rules, None)
    hid = hidden_cids(s, 0)
    assert not set(hid[0]) & set(s.zones["hand"][0])
    assert set(s.zones["hand"][1]) <= set(hid[1])


def test_known_pinned(rules):
    s = _state(rules, None)
    top = s.zones["deck"][1][0]
    assert top not in hidden_cids(s, 0, known=[top])[1]


def test_no_leak_of_true_order(rules):
    """真の山札順だけが違う2局面から、同じ seed で同じ決定化にはならない一方、観測は同じ（多重集合が同じ）。"""
    a = _state(rules, None)
    b = a.clone()
    z = b.zones["deck"][0]
    z.reverse()
    da, db = determinize(a, 0, 3), determinize(b, 0, 3)
    for owner in (0, 1):
        ha = hidden_cids(a, 0)[owner]
        assert sorted(da.cards[c].defn for c in ha) == sorted(db.cards[c].defn for c in ha)


def _rec(s, kind, cid, viewers):
    c = s.cards[cid]
    s.pub = getattr(s, "pub", [])
    s.pub.append({"n": len(s.pub), "turn": 0, "kind": kind, "viewers": viewers, "cid": cid, "gen": c.gen,
                  "defn": c.defn, "owner": c.owner, "zone": c.zone, "idx": 0})


def test_pub_look_and_reveal(rules):
    from dmsim.search import known_from_pub
    s = _state(rules, None)
    a, b = s.zones["deck"][1][0], s.zones["deck"][1][1]
    _rec(s, "look", a, [0])
    _rec(s, "reveal", b, [0, 1])
    assert known_from_pub(s, 0) == {a, b}
    assert known_from_pub(s, 1) == {b}
    assert a not in hidden_cids(s, 0)[1] and a in hidden_cids(s, 1)[1]
    d = determinize(s, 0, seed=9)
    assert d.cards[a].defn == s.cards[a].defn


def test_pub_stale_gen_ignored(rules):
    from dmsim.search import known_from_pub
    s = _state(rules, None)
    a = s.zones["deck"][1][0]
    _rec(s, "look", a, [0])
    s.cards[a].gen += 1
    assert known_from_pub(s, 0) == set()
