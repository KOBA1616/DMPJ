from tools.suggest_prep import prep_sources, scan


def test_prep_sources():
    c = {"name": "x", "effects": [{"op": "move", "select": {"zone": "hand", "owner": "you"}, "to": "graveyard"}]}
    assert prep_sources(c) == {"hand"}
    assert prep_sources({"name": "y", "effects": [{"op": "move", "select": {"zone": "hand", "owner": "opp"}, "to": "graveyard"}]}) == set()


def test_scan_runs():
    assert isinstance(scan(), list)
