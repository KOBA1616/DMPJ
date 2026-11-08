from tools.suggest_prep import prep_sources, scan


def test_prep_sources():
    c = {"name": "x", "effects": [{"op": "move", "select": {"zone": "hand", "owner": "you"}, "to": "graveyard"}]}
    assert prep_sources(c) == {"hand"}
    assert prep_sources({"name": "y", "effects": [{"op": "move", "select": {"zone": "hand", "owner": "opp"}, "to": "graveyard"}]}) == set()


def test_scan_runs():
    assert isinstance(scan(), list)


def test_add_prep_proposer():
    import random
    from dmsim.deckplan import change as C
    from dmsim.deckplan.spec import DeckProposal, Entry
    p = DeckProposal("d", [Entry("ダミー", 4)])
    chs = C.PROPOSERS["add_prep"](p, random.Random(0), n=3)
    assert chs and all(c.kind == "add_prep" and sum(d for _, d in c.ops) == 0 for c in chs)
