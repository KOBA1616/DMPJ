"""語彙拡張: サイレントスキル（501.1a。ターンのはじめにタップされていたら、アンタップしないかわりに能力を使ってもよい）。"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def keys(d):
    return [o["key"] for o in d["options"]]


def test_silent_skill_keeps_tapped_and_resolves(rr):
    """アンタップしないことを選ぶと、タップのまま能力が解決される。"""
    e = setup(rr, {"bz": ["R058"]})
    e.s.cards[0].tapped = True
    d = e.advance()
    while d["kind"] != "choose_cards" or "R058" not in "".join(keys(d)):
        e.answer([keys(d).index("pass")] if "pass" in keys(d) else [0])
        d = e.advance()
        assert d is not None
    hand = len(e.zlist("hand", 0))
    e.answer([0])                                              # R058 を選ぶ（アンタップしない）
    e.advance()
    assert e.s.cards[0].tapped
    assert len(e.zlist("hand", 0)) >= hand + 1


def test_declining_silent_skill_untaps_normally(rr):
    """サイレントスキルを使わなければ、通常どおりアンタップする（能力は解決されない）。"""
    e = setup(rr, {"bz": ["R058"]})
    e.s.cards[0].tapped = True
    d = e.advance()
    assert d["kind"] == "choose_cards" and "R058" in "".join(keys(d))
    hand = len(e.zlist("hand", 0))
    e.answer([])
    e.advance()
    assert not e.s.cards[0].tapped
    assert len(e.zlist("hand", 0)) == hand


def test_untapped_creature_is_not_offered_the_skill(rr):
    """ターンのはじめにタップされていなければ使えない。"""
    e = setup(rr, {"bz": ["R058"]})
    d = e.advance()
    assert d is None or "R058" not in "".join(keys(d)) or d["kind"] != "choose_cards"
