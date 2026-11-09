import random

from dmsim.deckplan import change as C
from dmsim.deckplan.pool import classify, support_names
from dmsim.deckplan.spec import DeckProposal, Entry


def test_classify_roles():
    assert classify({"abilities": [{"effect": [{"op": "draw", "count": 1}]}]}) == {"draw"}
    assert classify({"abilities": [{"effect": [{"op": "draw", "player": "opp", "count": 1}]}]}) == set()
    assert "accel" in classify({"abilities": [{"effect": [{"op": "mana_put", "select": {"zone": "deck", "owner": "you", "from_top": 1}}]}]})
    assert "search" in classify({"abilities": [{"effect": [{"op": "move", "select": {"zone": "deck", "owner": "you"}, "to": "hand"}]}]})


def test_support_fits_civs_and_proposer():
    pool = [{"name": "A", "cost": 2, "civs": ["water"], "roles": ["draw"]}, {"name": "B", "cost": 2, "civs": ["fire"], "roles": ["draw"]}]
    s = support_names({"water"}, pool=pool)
    assert s["draw"] == ["A"]
    deck = DeckProposal("d", [Entry("X", 4), Entry("Core", 1)])
    chs = C.PROPOSERS["add_support"](deck, random.Random(0), [], n=3, support=s, protect={"Core"})
    assert chs and all(c.ops == [("X", -1), ("A", 1)] for c in chs)
