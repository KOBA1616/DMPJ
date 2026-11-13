"""語彙パイロット第66弾: colorless（無色フィルタ）。

「無色カード」は filter: {colorless: true} で表す。
文明を持たないカード（civs が空）を対象とする。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-cl",
    "name": "試験無色獣",
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 4,
    "power": 4000,
    "races": ["テスト"],
    "text": "無色カードを対象とする。",
    "abilities": [
        {"kind": "static",
         "affects": {"zone": "deck", "owner": "you",
                     "filter": {"colorless": True}},
         "mod": {"power": 0}},
    ],
    "source": {"official": "test-cl", "review": "pending"},
}


def test_colorless_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    assert ab["affects"]["filter"]["colorless"] is True


def test_colorless_filter_key():
    # colorless が FILTER_KEYS に含まれることを確認
    from dmsim.cards.defs import FILTER_KEYS
    assert "colorless" in FILTER_KEYS
