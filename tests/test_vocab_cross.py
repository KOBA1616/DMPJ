"""語彙拡張: クロスギアのクロス（303.3, 303.4a, 303.5, 504.2）とクロスしたクリーチャーへの参照 crossed。"""
from pathlib import Path

import pytest
from conftest import answer, setup

from dmsim.cards.defs import card_yaml_files, load_rules


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def board(rr):
    e = setup(rr, {"bz": ["R053", "T001"], "mana": ["T001", "T001"], "hand": ["T001"]})
    e.s.cards[bz(e, 0, "T001")].entered_turn = -1
    return e


def to_main(e):
    answer(e, "charge", "pass")
    return e.advance()


def cross(e):
    answer(e, "main", "cross:R053:T001")
    d = e.advance()
    e.answer([0])                                             # マナの支払い
    return d


def test_cross_pays_cost_again_and_buffs_creature(rr):
    """303.3b コストをもう一度支払ってクロス。常在型はクロスしたクリーチャーだけに及ぶ。"""
    e = board(rr)
    c = bz(e, 0, "T001")
    assert e.chars(c)["power"] == 2000 and "blocker" not in e.chars(c)["keywords"]
    d = to_main(e)
    assert "cross:R053:T001" in [o["key"] for o in d["options"]]
    cross(e)
    assert sum(e.s.cards[m].tapped for m in e.zlist("mana", 0)) == 2
    assert e.chars(c)["power"] == 3500 and "blocker" in e.chars(c)["keywords"]


def test_cannot_cross_without_mana(rr):
    e = setup(rr, {"bz": ["R053", "T001"], "hand": ["T001"]})
    d = to_main(e)
    assert not any(o["key"].startswith("cross:") for o in d["options"])


def test_cross_again_onto_same_creature_not_allowed(rr):
    """303.4a クロスしているクリーチャー自身にはクロスしなおせない。"""
    e = board(rr)
    e.s.cards[bz(e, 0, "R053")].crossed = e.s.ref(bz(e, 0, "T001"))
    d = to_main(e)
    assert not any(o["key"].startswith("cross:") for o in d["options"])


def test_gear_stays_when_creature_leaves_and_trigger_fires(rr):
    """303.5 クロスされたクリーチャーが離れてもクロスギアは残る。破壊された時の誘発はクロスしていたことを見る。"""
    e = board(rr)
    c = bz(e, 0, "T001")
    e.s.cards[bz(e, 0, "R053")].crossed = e.s.ref(c)
    hand = len(e.zlist("hand", 0))
    e._push(e.ev_task({"ev": "move", "subject": e.s.ref(c), "to": "graveyard", "reason": "destroy"}))
    e.advance()
    assert bz(e, 0, "R053") is not None
    assert len(e.zlist("hand", 0)) >= hand + 1
    gear = e.s.cards[bz(e, 0, "R053")]
    assert not e.s.alive(gear.crossed)
