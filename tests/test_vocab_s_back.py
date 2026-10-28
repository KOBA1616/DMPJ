"""語彙拡張: S・バック（112.3b。シールドから手札に加わる時、そのカードを捨ててもよい。そうした場合、コストを支払わずに実行する）。"""
from pathlib import Path

import pytest
from conftest import answer, setup

from dmsim.defs import card_yaml_files, load_rules


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def names(e, zone, p=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def attack(rr, hand):
    e = setup(rr, {"bz": ["T005"]}, {"shield": ["R060"] * 5, "hand": hand})
    answer(e, "attack", "attack:T005:player")
    d = e.advance()
    assert d["kind"] == "choose_shields"
    e.answer([0, 1])
    return e


def test_s_back_creature_discards_and_summons_free(rr):
    """光のカードが手札に加わる時、捨てて S・バックのクリーチャーをコストなしで召喚できる。"""
    e = attack(rr, ["R065"])
    d = e.advance()
    assert d["kind"] == "declare_sback" and d["player"] == 1
    assert len(d["options"]) == 2                              # 割られた2枚のどちらを捨てるか
    e.answer([0])
    e.advance()
    assert "R065" in names(e, "bz", 1) and "R065" not in names(e, "hand", 1)
    assert names(e, "graveyard", 1) == ["R060"]                # 捨てた1枚
    assert "R060" in names(e, "hand", 1)                   # もう1枚は手札に残る
    assert len(e.zlist("shield", 1)) == 3


def test_s_back_spell_is_cast_free(rr):
    e = attack(rr, ["R066"])
    d = e.advance()
    assert d["kind"] == "declare_sback"
    e.answer([0])
    e.advance()
    assert names(e, "graveyard", 1).count("R066") == 1 and names(e, "graveyard", 1).count("R060") == 1
    assert len(e.zlist("hand", 1)) == 4                        # 残った1枚 + 呪文で2枚 + 相手のターンのドロー


def test_s_back_can_be_declined(rr):
    e = attack(rr, ["R065"])
    d = e.advance()
    assert d["kind"] == "declare_sback"
    e.answer([])
    e.advance()
    assert "R065" in names(e, "hand", 1) and names(e, "graveyard", 1) == []


def test_s_back_needs_matching_civilization(rr):
    """文明が合わないカード（水のシールド）では S・バックを宣言できない。"""
    e = setup(rr, {"bz": ["T005"]}, {"shield": ["R066"] * 5, "hand": ["R065"]})
    answer(e, "attack", "attack:T005:player")
    d = e.advance()
    e.answer([0, 1])
    d = e.advance()
    assert d is None or d["kind"] != "declare_sback"
