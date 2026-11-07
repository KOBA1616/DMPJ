"""語彙パイロット第83弾: evolution_existence_filter（進化クリーチャーの有無）。

「自分の進化クリーチャーがなければ」は filter: {evolution: true} + exists + not で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-eef",
    "name": "試験進化確認呪文",
    "types": ["spell"],
    "civs": ["water"],
    "cost": 3,
    "text": "カードを２枚引く。自分の進化クリーチャーがなければ、自分の手札を１枚捨てる。",
    "spell": [
        {"op": "draw", "count": 2},
        {"op": "if",
         "cond": {"not": {"exists": {"zone": "bz", "owner": "you",
                                     "filter": {"evolution": True}}}},
         "then": [
             {"op": "discard", "select": {"zone": "hand", "owner": "you", "count": 1}},
         ]},
    ],
    "source": {"official": "test-eef", "review": "pending"},
}


def test_evolution_existence_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    cond = card.spell[1]["cond"]
    assert cond["not"]["exists"]["filter"]["evolution"] is True


def test_evolution_existence_positive():
    card2 = {
        "id": "test-eef2",
        "name": "試験進化確認獣",
        "types": ["creature"],
        "civs": ["nature"],
        "cost": 4,
        "power": 4000,
        "races": ["テスト"],
        "text": "このクリーチャーが出た時、自分の進化クリーチャーがあれば、カードを１枚引く。",
        "abilities": [
            {"kind": "trigger",
             "when": {"event": "summon", "subject": "self"},
             "if": {"exists": {"zone": "bz", "owner": "you",
                               "filter": {"evolution": True}}},
             "effect": [{"op": "draw", "count": 1}]},
        ],
        "source": {"official": "test-eef2", "review": "pending"},
    }
    parsed = parse_card(card2, TABLES)
    assert parsed is not None
