"""語彙パイロット第95弾: mana_evolution（マナ進化）。

「マナ進化」は evolve_from + evolve_zone: mana で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-me",
    "name": "試験マナ進化獣",
    "types": ["creature", "evolution"],
    "civs": ["nature"],
    "cost": 6,
    "power": 6000,
    "races": ["テスト"],
    "text": "マナ進化：自然のクリーチャーを１体自分のマナゾーンから選び、このクリーチャーをその上に重ねつつ出す。",
    "evolve_from": {"civs": ["nature"], "types": ["creature"]},
    "evolve_zone": "mana",
    "abilities": [],
    "source": {"official": "test-me", "review": "pending"},
}


def test_mana_evolution_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    assert "evolution" in card.types


def test_mana_evolution_zone():
    card = parse_card(CARD, TABLES)
    assert card.evolve_zone == "mana"
