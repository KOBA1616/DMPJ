"""語彙パイロット第72弾: summon_from_mana_or_graveyard（マナゾーンまたは墓地から召喚）。

「マナゾーンまたは墓地から召喚してもよい」は既存キーワード2つの併記で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-smg",
    "name": "試験双召獣",
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 4,
    "power": 4000,
    "races": ["テスト"],
    "keywords": ["summon_from_mana", "summon_from_graveyard"],
    "text": "このクリーチャーを、自分のマナゾーンまたは墓地から召喚してもよい。",
    "source": {"official": "test-smg", "review": "pending"},
}


def test_both_summon_keywords_parse():
    card = parse_card(CARD, TABLES)
    assert card is not None
    assert "summon_from_mana" in card.keywords
    assert "summon_from_graveyard" in card.keywords


def test_keywords_defined():
    import yaml
    with open("data/rules/keywords.yaml") as f:
        kws = yaml.safe_load(f)["keywords"]
    assert "summon_from_mana" in kws
    assert "summon_from_graveyard" in kws
