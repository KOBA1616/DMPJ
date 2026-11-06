"""語彙パイロット第97弾: night_magic（ナイト・マジック）。

「バトルゾーンに自分のナイトがあれば、この呪文の能力をもう一度使ってもよい」は
spell の効果の後に if（exists ナイト）+ may で効果を再実行する形で表す。新語彙なし。
先例: dm28-016 魔弾プラス・ワン。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-nm",
    "name": "試験魔弾",
    "types": ["spell"],
    "civs": ["light"],
    "cost": 2,
    "races": ["ナイト"],
    "text": "カードを１枚引く。ナイト・マジック",
    "spell": [
        {"op": "draw", "count": 1},
        {"op": "if",
         "cond": {"exists": {"zone": "bz", "owner": "you",
                             "filter": {"race_has": "ナイト"}}},
         "then": [
             {"op": "may", "body": [
                 {"op": "draw", "count": 1},
             ]},
         ]},
    ],
    "source": {"official": "test-nm", "review": "pending"},
}


def test_night_magic_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    assert len(card.spell) == 2


def test_night_magic_structure():
    card = parse_card(CARD, TABLES)
    second = card.spell[1]
    assert second["op"] == "if"
    assert second["then"][0]["op"] == "may"
