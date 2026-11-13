"""語彙パイロット第75弾: battle_trigger（バトルする時）。

「このクリーチャーがバトルする時」は battle_start イベントで表す。攻撃側は subject: self、
守備側（攻撃先になった時）は when の opponent: self（本弾で追加）で受ける。
バトル相手は攻撃側では ref: event.opponent、守備側では ref: event.subject。
"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-bt",
    "name": "試験バトル獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "このクリーチャーがバトルする時、バトルしている相手のクリーチャーを持ち主の手札に戻してもよい。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "battle_start", "subject": "self"},
         "effect": [
             {"op": "may", "body": [
                 {"op": "bounce", "select": {"ref": "event.opponent"}},
             ]},
         ]},
        {"kind": "trigger",
         "when": {"event": "battle_start", "opponent": "self"},
         "effect": [
             {"op": "may", "body": [
                 {"op": "bounce", "select": {"ref": "event.subject"}},
             ]},
         ]},
    ],
    "source": {"official": "test-bt", "review": "pending"},
}


def test_battle_trigger_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    trigs = [a for a in card.abilities if a["kind"] == "trigger"]
    assert len(trigs) == 2
    assert trigs[0]["when"]["subject"] == "self"
    assert trigs[1]["when"]["opponent"] == "self"


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def keys(d):
    return [o["key"] for o in d["options"]]


def to_attack(e):
    d = e.advance()
    while d["kind"] in ("charge", "main"):
        e.answer([keys(d).index("pass")])
        d = e.advance()
    assert d["kind"] == "attack", d["kind"]
    return d


def by(e, defn, player=0):
    return next(c for c in e.bz_tops(player) if e.s.cards[c].defn == defn)


def test_battle_trigger_when_attacking(rr):
    """R075（3000）がタップした R076（2000）を攻撃: バトル開始時に R076 を手札へ戻せる。"""
    e = setup(rr, {"bz": ["R075"]}, {"bz": ["R076"]})
    e.s.cards[e.bz_tops(1)[0]].tapped = True
    d = to_attack(e)
    e.answer([keys(d).index("attack:R075:R076")])
    d = e.advance()
    if d is not None and d["kind"] == "block":
        e.answer([keys(d).index("no_block")])
        d = e.advance()
    assert d["kind"] == "yes_no"          # バトルする時: 戻してもよいか
    e.answer([0])                          # はい
    e.advance()
    assert e.bz_tops(1) == []              # R076 はバトルゾーンを離れた
    assert [c.defn for c in e.s.cards if c.zone == "hand" and c.defn == "R076"]


def test_battle_trigger_when_attacked(rr):
    """タップした R075 が R070（4000）に攻撃される: バトル開始時に攻撃側 R070 を手札へ戻せる。"""
    e = setup(rr, {"bz": ["R070"]}, {"bz": ["R075"]})
    e.s.cards[by(e, "R075", 1)].tapped = True
    d = to_attack(e)
    e.answer([keys(d).index("attack:R070:R075")])
    d = e.advance()
    if d is not None and d["kind"] == "block":
        e.answer([keys(d).index("no_block")])
        d = e.advance()
    assert d["kind"] == "yes_no"          # 守備側のバトル誘発
    e.answer([0])
    e.advance()
    assert e.bz_tops(0) == []              # R070 は手札へ戻った
    assert [c.defn for c in e.s.cards if c.zone == "hand" and c.defn == "R070"]
