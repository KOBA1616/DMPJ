"""語彙パイロット第114弾: random_discard（見ないで選び捨てさせる）。

「相手の手札を1枚見ないで選び、捨てさせる」は discard op
（select zone: hand, owner: opp）で表す。手札は秘匿ゾーンのため
選択は見ないで行われる。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-rd",
    "name": "試験盲捨獣",
    "types": ["creature"],
    "civs": ["darkness"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "このクリーチャーが出た時、相手の手札を１枚見ないで選び、捨てさせる。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "move", "subject": "self", "to": "bz"},
         "effect": [
             {"op": "discard",
              "select": {"zone": "hand", "owner": "opp", "count": 1}},
         ]},
    ],
    "source": {"official": "test-rd", "review": "pending"},
}


def test_random_discard_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    # discard は parse 時に move（reason: discard）へ正規化される
    step = ab["effect"][0]
    assert step["op"] == "move"
    assert step["to"] == "graveyard"
    assert step["reason"] == "discard"


def test_random_discard_select_shape():
    card = parse_card(CARD, TABLES)
    sel = card.abilities[0]["effect"][0]["select"]
    assert sel["zone"] == "hand"
    assert sel["owner"] == "opp"
    assert sel["count"] == 1
