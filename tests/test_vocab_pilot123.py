"""語彙パイロット第123弾: mana_all_civilizations（マナゾーンのカードをすべての文明として扱う）。

「自分のマナゾーンにあるカードを、すべての文明のカードとして扱う」は
static {affects: {zone: mana, owner: you}, mod: {add_civs: [全5文明]}} で表す。
支払い判定（turn._mana_choices）がマナカードの文明を定義ではなく特性（chars）で
見るようエンジンを拡張し、add_civs が支払いに効くようにした。
"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-mac",
    "name": "試験薫風妖精",
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 2,
    "power": 1000,
    "races": ["テスト"],
    "text": "自分のマナゾーンにあるカードを、すべての文明のカードとして扱う。",
    "abilities": [
        {"kind": "static", "affects": {"zone": "mana", "owner": "you"},
         "mod": {"add_civs": ["light", "water", "darkness", "fire", "nature"]}},
    ],
    "source": {"official": "test-mac", "review": "pending"},
}


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def test_mana_all_civilizations_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["mod"]["add_civs"] == ["light", "water", "darkness", "fire", "nature"]


def _choices(e, defn="R088"):
    cid = next(i for i, c in enumerate(e.s.cards) if c.defn == defn)
    return e._mana_choices(cid, 0)


def test_mana_counts_as_all_civilizations(rr):
    """R087 がいる時、自然のマナで火コスト（文明: 火）の支払いができる。"""
    e = setup(rr, {"bz": ["R087"], "hand": ["R088"], "mana": ["R070", "R070"]}, {})
    assert _choices(e) != []


def test_mana_without_fairy_cannot_pay(rr):
    """R087 がいなければ、自然のマナでは火の文明を満たせない。"""
    e = setup(rr, {"hand": ["R088"], "mana": ["R070", "R070"]}, {})
    assert _choices(e) == []
