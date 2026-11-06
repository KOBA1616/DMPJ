"""語彙パイロット第143弾: leave_stay（離れるかわりにとどまる）。

「相手のナイトがある時、離れるかわりにとどまる」は条件付き static の
mod: {no_leave: true}（第49弾）で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-ls",
    "name": "試験残留騎士",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 5,
    "power": 4000,
    "races": ["テスト"],
    "text": "バトルゾーンに相手のナイトがあり、このクリーチャーがバトルゾーンを離れる時、このクリーチャーはバトルゾーンを離れるかわりにとどまる。",
    "abilities": [
        {"kind": "static", "affects": "self",
         "if": {"exists": {"zone": "bz", "owner": "opp", "filter": {"race_has": "ナイト"}}},
         "mod": {"no_leave": True}},
    ],
    "source": {"official": "test-ls", "review": "pending"},
}


def test_leave_stay_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"


def test_leave_stay_shape():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["mod"]["no_leave"] is True
    assert ab["if"]["exists"]["filter"]["race_has"] == "ナイト"
