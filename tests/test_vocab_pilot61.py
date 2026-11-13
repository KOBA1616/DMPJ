"""語彙パイロット第61弾: win_all_battles（すべてのバトルに勝つ）。

「このクリーチャーはすべてのバトルに勝つ」は static の
mod: {win_all_battles: true} で表す。
combat._battle でパワー比較より優先して勝敗を決める。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-wab",
    "name": "試験必勝獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 5,
    "power": 1000,
    "races": ["テスト"],
    "text": "このクリーチャーはすべてのバトルに勝つ。",
    "abilities": [
        {"kind": "static", "affects": "self",
         "mod": {"win_all_battles": True}},
    ],
    "source": {"official": "test-wab", "review": "pending"},
}


def test_win_all_battles_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    assert ab["mod"]["win_all_battles"] is True


def test_win_all_battles_invalid():
    bad = {
        "id": "test-wab-bad",
        "name": "試験必勝獣不良",
        "types": ["creature"],
        "civs": ["fire"],
        "cost": 5,
        "power": 1000,
        "abilities": [
            {"kind": "static", "affects": "self",
             "mod": {"win_all_battles": "yes"}},
        ],
        "source": {"official": "test-wab-bad", "review": "pending"},
    }
    try:
        parse_card(bad, TABLES)
        assert False, "should have raised"
    except Exception as e:
        assert "win_all_battles" in str(e)
