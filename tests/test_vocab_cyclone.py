"""語彙拡張: サイクロン（唱える直前にクリーチャーを召喚していれば、唱えた後に墓地ではなく手札に戻す）。"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def keys(d):
    return [o["key"] for o in d["options"]]


def play(e, name):
    """メインで name の実行を選ぶ（マナチャージは見送り、支払いは先頭の候補）。"""
    d = e.advance()
    while d["kind"] == "charge":
        e.answer([keys(d).index("pass")])
        d = e.advance()
    e.answer([keys(d).index("play:" + name)])
    d = e.advance()
    while d is not None and d["kind"] == "pay_mana":
        e.answer([0])
        d = e.advance()
    return d


def zone_names(e, zone):
    return [e.s.cards[c].defn for c in e.zlist(zone, 0)]


def test_cyclone_returns_spell_after_summon(rr):
    """召喚した直後に唱えると、サイクロン呪文は墓地ではなく手札に戻る。"""
    e = setup(rr, {"hand": ["R060", "R062"], "mana": ["R060"] * 3})
    play(e, "R060")
    play(e, "R062")
    e.advance()
    assert "R062" in zone_names(e, "hand") and "R062" not in zone_names(e, "graveyard")


def test_cyclone_without_summon_goes_to_graveyard(rr):
    e = setup(rr, {"hand": ["R062"], "mana": ["R060"] * 3})
    play(e, "R062")
    e.advance()
    assert "R062" in zone_names(e, "graveyard")


def test_cyclone_needs_summon_immediately_before(rr):
    """召喚のあとに別の呪文を挟むと「直前」ではないので、手札に戻らない。"""
    e = setup(rr, {"hand": ["R060", "R064", "R062"], "mana": ["R060"] * 4})
    play(e, "R060")
    play(e, "R064")
    play(e, "R062")
    e.advance()
    assert "R062" in zone_names(e, "graveyard")


def test_granted_cyclone(rr):
    """「自分が唱える呪文はすべてサイクロンを得る」: 通常の呪文も召喚直後なら手札に戻る。"""
    e = setup(rr, {"hand": ["R063", "R064"], "mana": ["R060"] * 3})
    play(e, "R063")
    play(e, "R064")
    e.advance()
    assert "R064" in zone_names(e, "hand")
