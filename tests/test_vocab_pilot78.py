"""語彙パイロット第78弾: shield_event_trigger（シールドゾーンに置かれた時）。

「自分のシールドゾーンにカードが置かれた時」は move イベント + to: shield で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-set",
    "name": "試験盾獣",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 5,
    "power": 5000,
    "races": ["テスト"],
    "text": "自分のシールドゾーンにカードが置かれた時、カードを１枚引いてもよい。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "move", "to": "shield",
                  "subject": {"owner": "you"}},
         "effect": [
             {"op": "may", "body": [
                 {"op": "draw", "count": 1},
             ]},
         ]},
    ],
    "source": {"official": "test-set", "review": "pending"},
}


def test_shield_event_trigger_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"
    assert ab["when"]["to"] == "shield"


def test_shield_event_trigger_subject():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["when"]["subject"]["owner"] == "you"
