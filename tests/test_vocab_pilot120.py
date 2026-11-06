"""語彙パイロット第120弾: under_card_count（含まれるカードの数）。

「そのクリーチャーに含まれるカード１枚につき」は、含まれる総数を
{sum: [1, {count: {under_of: <変数名>}}]} で表す（under_of は下のカード、
本体1枚を加える）。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-ucc",
    "name": "試験含有数獣",
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "このクリーチャーが出た時、自分のクリーチャーを１体選ぶ。そのクリーチャーに含まれるカード１枚につき、カードを１枚引いてもよい。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "move", "subject": "self", "to": "bz"},
         "effect": [
             {"op": "choose",
              "select": {"zone": "bz", "owner": "you",
                         "filter": {"types": ["creature"]}, "count": 1},
              "as": "t"},
             {"op": "may", "body": [
                 {"op": "draw",
                  "count": {"sum": [1, {"count": {"under_of": "t"}}]}},
             ]},
         ]},
    ],
    "source": {"official": "test-ucc", "review": "pending"},
}


def test_under_count_expr_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    draw = card.abilities[0]["effect"][1]["body"][0]
    assert draw["count"] == {"sum": [1, {"count": {"under_of": "t"}}]}


def test_under_count_choose_binds():
    card = parse_card(CARD, TABLES)
    assert card.abilities[0]["effect"][0]["as"] == "t"
