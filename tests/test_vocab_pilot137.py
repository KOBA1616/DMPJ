"""語彙パイロット第137弾: god_filter（ゴッドのフィルタ・条件）。

「ゴッド」は種族 race_has: ゴッド で扱う。「そのクリーチャーがゴッドであれば」は
exists: {ref: X, filter: {race_has: ゴッド}}。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-gf",
    "name": "試験ゴッド滅ぼし",
    "types": ["spell"],
    "civs": ["darkness"],
    "cost": 4,
    "races": ["テスト"],
    "text": "相手のクリーチャーを１体破壊する。そのクリーチャーがゴッドであれば、相手のクリーチャーをもう１体破壊してもよい。",
    "spell": [
        {"op": "destroy",
         "select": {"zone": "bz", "owner": "opp", "count": 1, "filter": {"types": ["creature"]}},
         "as": "first"},
        {"op": "may",
         "if": {"exists": {"ref": "first", "filter": {"race_has": "ゴッド"}}},
         "body": [
             {"op": "destroy",
              "select": {"zone": "bz", "owner": "opp", "count": 1, "filter": {"types": ["creature"]}}},
         ]},
    ],
    "source": {"official": "test-gf", "review": "pending"},
}


def test_god_filter_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    assert len(card.spell) == 2


def test_god_filter_shape():
    card = parse_card(CARD, TABLES)
    cond = card.spell[1]["if"]["exists"]
    assert cond["ref"] == "first"
    assert cond["filter"]["race_has"] == "ゴッド"
