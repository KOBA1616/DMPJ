"""語彙パイロット第102弾: samurai_generate（侍流ジェネレート）。

「出た時、クロスギアを１枚、自分の手札からコストを支払わずにジェネレートしてもよい」は
may + play_free（クロスギアのプレイ＝ジェネレート）で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-sg",
    "name": "試験侍獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 4,
    "power": 3000,
    "races": ["サムライ"],
    "text": "侍流ジェネレート（このクリーチャーが出た時、クロスギアを１枚、自分の手札からコストを支払わずにジェネレートしてもよい）",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz", "subject": "self"},
         "effect": [
             {"op": "may", "body": [
                 {"op": "play_free",
                  "select": {"zone": "hand", "owner": "you",
                             "filter": {"types": ["cross_gear"]}, "count": 1}},
             ]},
         ]},
    ],
    "source": {"official": "test-sg", "review": "pending"},
}


def test_samurai_generate_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"


def test_samurai_generate_effect():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    may = ab["effect"][0]
    assert may["op"] == "may"
    assert may["body"][0]["op"] == "play_free"
