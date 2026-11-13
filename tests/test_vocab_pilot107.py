"""語彙パイロット第107弾: tap_event_trigger（タップした時）。

「このクリーチャーがタップした時、〜」は tap イベントの誘発そのもの
（第105弾の first_time なし版）で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-tet",
    "name": "試験踏鳴獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 4,
    "power": 4000,
    "races": ["テスト"],
    "text": "このクリーチャーがタップした時、カードを１枚引く。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "tap", "subject": "self"},
         "effect": [
             {"op": "draw", "count": 1},
         ]},
    ],
    "source": {"official": "test-tet", "review": "pending"},
}


def test_tap_trigger_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"


def test_tap_trigger_no_first_time():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["when"]["event"] == "tap"
    assert ab["when"]["subject"] == "self"
    # first_time は付けない（毎回誘発する）
    assert "first_time" not in ab
