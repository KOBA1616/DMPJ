"""語彙パイロット第92弾: summon_only_entry（召喚によって出た時）。

「召喚によって出た時」は when: {event: move, to: bz, reason: summon, subject: self} で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-soe",
    "name": "試験召喚限定獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 7,
    "power": 7000,
    "races": ["テスト"],
    "text": "このクリーチャーが召喚によって出た時、カードを１枚引く。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz", "reason": "summon", "subject": "self"},
         "effect": [
             {"op": "draw", "count": 1},
         ]},
    ],
    "source": {"official": "test-soe", "review": "pending"},
}


def test_summon_only_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"


def test_summon_only_reason():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["when"]["reason"] == "summon"
