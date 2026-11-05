"""語彙パイロット第105弾: first_tap_trigger（はじめてタップした時）。

「各ターン、このクリーチャーがはじめてタップした時、アンタップする」は
tap イベント + first_time: true で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-ftt",
    "name": "試験跳返獣",
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "各ターン、このクリーチャーがはじめてタップした時、アンタップする。",
    "abilities": [
        {"kind": "trigger",
         "first_time": True,
         "when": {"event": "tap", "subject": "self"},
         "effect": [
             {"op": "untap", "select": {"ref": "self"}},
         ]},
    ],
    "source": {"official": "test-ftt", "review": "pending"},
}


def test_first_tap_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"


def test_first_tap_flags():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["when"]["event"] == "tap"
    assert ab["first_time"] is True
