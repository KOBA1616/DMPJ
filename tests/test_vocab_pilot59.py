"""語彙パイロット第59弾: battle_indestructible（バトル中破壊されない）。

「バトル中、このクリーチャーは破壊されない」は static の
mod: {battle_indestructible: true} で表す。
combat._battle で敗者から除外する（勝敗判定はパワーどおり）。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-bi",
    "name": "試験不壊獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 3,
    "power": 3000,
    "races": ["テスト"],
    "text": "このクリーチャーはバトル中、破壊されない。",
    "abilities": [
        {"kind": "static", "affects": "self",
         "mod": {"battle_indestructible": True}},
    ],
    "source": {"official": "test-bi", "review": "pending"},
}


def test_battle_indestructible_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    assert ab["mod"]["battle_indestructible"] is True


def test_battle_indestructible_invalid():
    bad = {
        "id": "test-bi-bad",
        "name": "試験不壊獣不良",
        "types": ["creature"],
        "civs": ["fire"],
        "cost": 3,
        "power": 3000,
        "abilities": [
            {"kind": "static", "affects": "self",
             "mod": {"battle_indestructible": "yes"}},
        ],
        "source": {"official": "test-bi-bad", "review": "pending"},
    }
    try:
        parse_card(bad, TABLES)
        assert False, "should have raised"
    except Exception as e:
        assert "battle_indestructible" in str(e)
