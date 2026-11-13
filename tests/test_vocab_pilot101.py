"""語彙パイロット第101弾: summon_restriction（召喚制限）。

「すべてのプレイヤーは、コスト４以下のクリーチャーを召喚できない」は
affects を手札ゾーンに向けた static の deny: [summon] で表す。新語彙なし。
先例: 34-sec001。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-sr",
    "name": "試験封獣",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 7,
    "power": 7000,
    "races": ["テスト"],
    "text": "すべてのプレイヤーは、コスト４以下のクリーチャーを召喚できない。",
    "abilities": [
        {"kind": "static",
         "affects": {"zone": "hand", "owner": "any",
                     "filter": {"types": ["creature"], "cost_le": 4}},
         "mod": {"deny": ["summon"]}},
    ],
    "source": {"official": "test-sr", "review": "pending"},
}


def test_summon_restriction_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"


def test_summon_restriction_mod():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["mod"]["deny"] == ["summon"]
    assert ab["affects"]["zone"] == "hand"
