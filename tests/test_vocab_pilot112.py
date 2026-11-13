"""語彙パイロット第112弾: recast_from_graveyard（墓地から唱える）。

「コスト7以下の呪文を1枚、自分の墓地からコストを支払わずに唱える」は
play_free（select zone: graveyard, types: [spell]）で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-rfg",
    "name": "試験再唱呪文",
    "types": ["spell"],
    "civs": ["darkness"],
    "cost": 5,
    "power": None,
    "races": [],
    "text": "コスト7以下の呪文を1枚、自分の墓地からコストを支払わずに唱える。",
    "spell": [
        {"op": "play_free",
         "select": {"zone": "graveyard", "owner": "you",
                    "filter": {"types": ["spell"], "cost_le": 7},
                    "count": 1}},
    ],
    "source": {"official": "test-rfg", "review": "pending"},
}


def test_recast_play_free_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    step = card.spell[0]
    assert step["op"] == "play_free"
    assert step["select"]["zone"] == "graveyard"


def test_recast_filter_shape():
    card = parse_card(CARD, TABLES)
    f = card.spell[0]["select"]["filter"]
    assert f["types"] == ["spell"]
    assert f["cost_le"] == 7
