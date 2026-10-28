"""語彙拡張: ウェーブストライカー（キーワードは印、能力は if で「他に2体以上」を見る）と、誘発条件を誘発時にも見る規則（603.4）。"""
from pathlib import Path

import pytest
from conftest import answer, setup

from dmsim.defs import card_yaml_files, load_rules


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def play(rr, others):
    e = setup(rr, {"hand": ["R054"], "mana": ["T001"], "bz": ["R054"] * others})
    d = e.advance()
    assert d["kind"] == "charge"
    e.answer([[o["key"] for o in d["options"]].index("pass")])
    answer(e, "main", "play:R054")
    e.advance()
    return e


def hand(e):
    return len(e.zlist("hand", 0))


def test_ability_gained_only_with_two_other_wave_strikers(rr):
    """他に2体以上いる時だけ、出た時にカードを1枚引く。"""
    h0, h1, h2 = (hand(play(rr, n)) for n in (0, 1, 2))
    assert h0 == h1 and h2 == h1 + 1


def test_static_abilities_follow_the_condition(rr):
    """常在型も同じ条件で働く。自身への修整と自分のクリーチャー全体への修整のどちらも。"""
    two = setup(rr, {"bz": ["R055", "R054", "R054"]})
    pw = sorted(two.chars(c)["power"] for c in two.bz_tops(0))
    assert pw == [2000, 2000, 6000]                       # R055: 1000+4000+1000, R054 ×2: 1000+1000
    one = setup(rr, {"bz": ["R055", "R054"]})
    assert sorted(one.chars(c)["power"] for c in one.bz_tops(0)) == [1000, 1000]
