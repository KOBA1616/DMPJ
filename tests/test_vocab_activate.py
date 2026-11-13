"""語彙拡張: 起動型能力 kind: activate（602, 602.3a。攻撃する代わりにタップして使うタップ能力）。"""
from pathlib import Path

import pytest
from conftest import answer, setup

from dmsim.cards.defs import card_yaml_files, load_rules


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def keys(d):
    return [o["key"] for o in d["options"]]


def test_tap_ability_taps_self_and_resolves(rr):
    """602.1 タップ能力: 攻撃の代わりに自身をタップして効果を得る。"""
    e = setup(rr, {"bz": ["R050"]})
    e.s.cards[bz(e, 0, "R050")].entered_turn = -1
    hand = len(e.zlist("hand", 0))
    answer(e, "attack", "activate:R050:0")
    d = e.advance()
    assert e.s.cards[bz(e, 0, "R050")].tapped
    assert len(e.zlist("hand", 0)) == hand + 1
    assert "activate:R050:0" not in keys(d)                  # タップ済みなので二度は使えない


def test_summoning_sick_creature_cannot_activate(rr):
    """602.3a 召喚酔い中は攻撃ができないのでタップ能力も使えない。"""
    e = setup(rr, {"bz": ["R050"]})
    e.s.cards[bz(e, 0, "R050")].entered_turn = e.s.turn   # このターンに出たことにする
    d = e.advance()
    while d["player"] == 0 and d["kind"] in ("charge", "main"):
        e.answer([keys(d).index("pass")])
        d = e.advance()
    assert d["player"] == 1                               # 先攻の攻撃ステップは選べる行動が無く飛ばされる


def test_activate_requires_ability_to_attack(rr):
    """602.3a 効果で攻撃ができない状態でも使えない。"""
    e = setup(rr, {"bz": ["R052"]})
    e.s.cards[bz(e, 0, "R052")].entered_turn = -1
    d = e.advance()
    assert d["player"] == 1                               # 選べる行動が無いので先攻の攻撃ステップは飛ばされる


def test_activate_by_tapping_other_creature(rr):
    """「自分の光のクリーチャーをタップし」型: 条件に合う別のクリーチャーをタップして使う。"""
    e = setup(rr, {"bz": ["R051", "R051"]})
    for c in e.bz_tops(0):
        e.s.cards[c].entered_turn = -1
    d = e.advance()
    assert d["kind"] == "attack"
    assert "activate:R051:0" in keys(d)
