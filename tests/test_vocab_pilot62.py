"""語彙パイロット第62弾: add_civs（文明追加）。

「〜は〜のクリーチャーでもある」「文明に〜を追加する」は static の
mod: {add_civs: [...]} で表す。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-ac",
    "name": "試験染獣",
    "types": ["creature"],
    "civs": ["darkness"],
    "cost": 4,
    "power": 4000,
    "races": ["テスト"],
    "text": "バトルゾーンにある自分の闇のクリーチャーはすべて、火のクリーチャーでもある。",
    "abilities": [
        {"kind": "static",
         "affects": {"zone": "bz", "owner": "you",
                     "filter": {"types": ["creature"], "civs": ["darkness"]}},
         "mod": {"add_civs": ["fire"]}},
    ],
    "source": {"official": "test-ac", "review": "pending"},
}


def test_add_civs_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    assert ab["mod"]["add_civs"] == ["fire"]


def test_add_civs_invalid():
    bad = {
        "id": "test-ac-bad",
        "name": "試験染獣不良",
        "types": ["creature"],
        "civs": ["darkness"],
        "cost": 4,
        "power": 4000,
        "abilities": [
            {"kind": "static", "affects": "self",
             "mod": {"add_civs": ["invalid_civ"]}},
        ],
        "source": {"official": "test-ac-bad", "review": "pending"},
    }
    try:
        parse_card(bad, TABLES)
        assert False, "should have raised"
    except Exception as e:
        assert "add_civs" in str(e)
