"""語彙パイロット第84弾: evolution_gv（進化GV）。

「進化GV」は evolve_from + evolve_count: N で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-gv",
    "name": "試験GV獣",
    "types": ["creature", "evolution"],
    "civs": ["fire"],
    "cost": 8,
    "power": 9000,
    "races": ["テスト"],
    "text": "進化GV-自分のテスト３体を重ねた上に置く。",
    "evolve_from": {"race_has": "テスト"},
    "evolve_count": 3,
    "source": {"official": "test-gv", "review": "pending"},
}


def test_evolution_gv_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    assert card.evolve_count == 3


def test_evolution_gv_filter():
    card = parse_card(CARD, TABLES)
    assert card.evolve_from["race_has"] == "テスト"
