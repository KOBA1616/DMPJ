"""語彙パイロット第80弾: break_increase（ブレイク数増加）。

「シールドをさらにN枚ブレイクする」は mod: {breaks: N}（加算）で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-bi",
    "name": "試験増加獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 5,
    "power": 5000,
    "races": ["ヒューマノイド"],
    "text": "このクリーチャーがタップされている時、自分の他のヒューマノイドはすべて、シールドをさらに１枚ブレイクする。",
    "abilities": [
        {"kind": "static",
         "affects": {"owner": "you", "other": True,
                     "filter": {"race_has": "ヒューマノイド"}},
         "if": {"exists": {"ref": "self", "filter": {"tapped": True}}},
         "mod": {"breaks": 1}},
    ],
    "source": {"official": "test-bi", "review": "pending"},
}


def test_break_increase_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    assert ab["mod"]["breaks"] == 1


def test_break_increase_affects():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["affects"]["other"] is True
    assert ab["affects"]["filter"]["race_has"] == "ヒューマノイド"
