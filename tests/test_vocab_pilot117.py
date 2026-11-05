"""語彙パイロット第117弾: cost_lt_count（コストが数より小さい）。

選択フィルタの cost_le に {sum: [{count: ...}, -1]} を渡すことで
「（集計した数）よりコストが小さいカード」を表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-cltc",
    "name": "試験数勢探索",
    "types": ["spell"],
    "civs": ["nature"],
    "cost": 4,
    "power": None,
    "races": [],
    "text": "自分のマナゾーンにあるカードの数よりコストが小さいクリーチャーを１体、自分の山札から選び、手札に加える。",
    "spell": [
        {"op": "move",
         "select": {"zone": "deck", "owner": "you",
                    "filter": {"types": ["creature"],
                               "cost_le": {"sum": [{"count": {"zone": "mana", "owner": "you"}}, -1]}},
                    "count": 1},
         "to": "hand", "reason": "put"},
    ],
    "source": {"official": "test-cltc", "review": "pending"},
}


def test_cost_lt_count_expr_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    f = card.spell[0]["select"]["filter"]
    assert f["cost_le"] == {"sum": [{"count": {"zone": "mana", "owner": "you"}}, -1]}


def test_cost_lt_count_shape():
    card = parse_card(CARD, TABLES)
    assert card.spell[0]["select"]["zone"] == "deck"
