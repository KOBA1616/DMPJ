"""語彙パイロット第115弾: filter_not_race（〜でないクリーチャー）。

選択フィルタの「ドラゴンでないクリーチャー」は第81弾の
filter not_race_has で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-fnr",
    "name": "試験非竜討伐",
    "types": ["spell"],
    "civs": ["fire"],
    "cost": 4,
    "power": None,
    "races": [],
    "text": "ドラゴンでない相手のクリーチャーを１体破壊する。",
    "spell": [
        {"op": "destroy",
         "select": {"zone": "bz", "owner": "opp",
                    "filter": {"not_race_has": "ドラゴン"},
                    "count": 1}},
    ],
    "source": {"official": "test-fnr", "review": "pending"},
}


def test_not_race_filter_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    step = card.spell[0]
    assert step["select"]["filter"]["not_race_has"] == "ドラゴン"


def test_not_race_spell_shape():
    card = parse_card(CARD, TABLES)
    # destroy は parse 時に move（reason: destroy）へ正規化される
    step = card.spell[0]
    assert step["op"] == "move"
    assert step["reason"] == "destroy"
    assert step["select"]["owner"] == "opp"
