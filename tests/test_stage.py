from types import SimpleNamespace as NS

from dmsim.eval import progress
from dmsim.eval.stage import board_met, cards_met, count_matching, parts_to_cards, zone_counts
from dmsim.search.leaf_parts import Part, PartsSpec, parts_score


class FakeEng:
    def __init__(self, zones, types=None):
        self.zones, self.types = zones, types or {}
        self.s = NS(cards={c: NS(defn=d) for z in zones.values() for c, d in z})

    def zlist(self, zone, p):
        if zone not in self.zones:
            raise KeyError(zone)
        return [c for c, _ in self.zones[zone]]

    def chars(self, cid):
        return {"types": self.types.get(cid, ["creature"])}


def eng():
    return FakeEng({"hand": [(1, "A"), (2, "A")], "graveyard": [(3, "B")], "bz": [(4, "C")], "mana": [], "shield_bz": []})


def test_counts_and_met():
    e = eng()
    assert zone_counts(e, 0, "hand")["A"] == 2
    assert count_matching(e, 0, "hand", ("A",)) == 2 and count_matching(e, 0, "bz") == 1
    assert board_met(e, 0, {"hand": {"A": 2}, "graveyard": {"B": 1}})
    assert not board_met(e, 0, {"hand": {"A": 3}})
    assert cards_met(e, 0, {"A": 2, "B": 1}) and not cards_met(e, 0, {"D": 1}) and not cards_met(e, 0, {})


def test_progress_and_leaf_share():
    e = eng()
    spec = progress.ProgressSpec(board={"hand": {"A": 1}}, cards={"B": 1})
    assert progress.board_ok(e, 0, spec) and progress.cards_ok(e, 0, spec)
    parts = PartsSpec((Part("hand", ("A",), 2, 1.0), Part("graveyard", ("B",), 1, 0.5)), coef=10)
    assert parts_score(e, 0, parts) == 10 * (2 + 0.5)
    assert parts_to_cards(parts.parts) == {"A": 2, "B": 1}
    assert cards_met(e, 0, parts_to_cards(parts.parts))
