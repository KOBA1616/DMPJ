"""語彙パイロット第90弾: enters_battle_zone_tapped（タップして出る）。

「〜はタップして出る」は static + mod: {grant: [enters_tapped]} で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-ebt",
    "name": "試験拘束獣",
    "types": ["creature"],
    "civs": ["darkness"],
    "cost": 5,
    "power": 4000,
    "races": ["テスト"],
    "text": "相手の進化クリーチャーは、タップして出る。",
    "abilities": [
        {"kind": "static",
         "affects": {"zone": "bz", "owner": "opp",
                     "filter": {"evolution": True}},
         "mod": {"grant": ["enters_tapped"]}},
    ],
    "source": {"official": "test-ebt", "review": "pending"},
}


def test_enters_tapped_grant_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    assert ab["mod"]["grant"] == ["enters_tapped"]


def test_enters_tapped_affects():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["affects"]["filter"]["evolution"] is True
