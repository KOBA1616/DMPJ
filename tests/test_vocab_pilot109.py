"""語彙パイロット第109弾: shield_trigger_grant（S・トリガー付与）。

「自分のシールドゾーンにある光のカードはすべて『S・トリガー』を得る」は
static の affects + mod grant: [s_trigger] で表す（dm24ex4-015 先例）。
新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-stg",
    "name": "試験トリガー付与塔",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 5,
    "power": 4000,
    "races": ["テスト"],
    "text": "自分のシールドゾーンにある光のカードはすべて「S・トリガー」を得る。",
    "abilities": [
        {"kind": "static",
         "affects": {"zone": "shield", "owner": "you",
                     "filter": {"civs": ["light"]}},
         "mod": {"grant": ["s_trigger"]}},
    ],
    "source": {"official": "test-stg", "review": "pending"},
}


def test_s_trigger_grant_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    assert ab["mod"]["grant"] == ["s_trigger"]


def test_s_trigger_grant_affects():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["affects"]["zone"] == "shield"
    assert ab["affects"]["filter"]["civs"] == ["light"]
