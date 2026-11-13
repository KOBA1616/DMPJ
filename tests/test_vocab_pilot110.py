"""語彙パイロット第110弾: battle_win_all（すべてのバトルに勝つ）。

「このクリーチャーはすべてのバトルに勝つ」は第61弾の
mod: {win_all_battles: true} で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-bwa",
    "name": "試験不敗獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 6,
    "power": 6000,
    "races": ["テスト"],
    "text": "このクリーチャーは、すべてのバトルに勝つ。",
    "abilities": [
        {"kind": "static",
         "mod": {"win_all_battles": True}},
    ],
    "source": {"official": "test-bwa", "review": "pending"},
}


def test_win_all_battles_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    assert ab["mod"]["win_all_battles"] is True


def test_win_all_battles_static_only():
    card = parse_card(CARD, TABLES)
    assert len(card.abilities) == 1
