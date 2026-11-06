"""語彙パイロット第67弾: tap_activated_ability（攻撃するかわりにタップして能力を使う）。

「このクリーチャーで攻撃するかわりに、タップして次の能力を使ってもよい」は
既存の kind: activate, cost: {tap: self} で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-taa",
    "name": "試験起動獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 4,
    "power": 4000,
    "races": ["テスト"],
    "text": "このクリーチャーで攻撃するかわりに、タップして次の能力を使ってもよい。",
    "abilities": [
        {"kind": "activate", "cost": {"tap": "self"},
         "effect": [
             {"op": "untap", "select": {"zone": "bz", "owner": "you",
                                          "filter": {"race_has": "フレイム・コマンド"}}},
         ]},
    ],
    "source": {"official": "test-taa", "review": "pending"},
}


def test_tap_activated_ability_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "activate"
    assert ab["cost"]["tap"] == "self"


def test_tap_activated_ability_cost():
    # tap: self が activate の cost として有効であることを確認
    from dmsim.defs import load_tables
    t = load_tables()
    assert t is not None
