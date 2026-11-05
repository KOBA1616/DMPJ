"""語彙パイロット第79弾: civ_count（文明の種類数）。

「バトルゾーンにある相手の文明ひとつにつき」は既存の式 civ_count で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-cc",
    "name": "試験文明獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 6,
    "power": 6000,
    "races": ["テスト"],
    "text": "このクリーチャーは、バトルゾーンにある相手の文明ひとつにつき１枚、シールドを追加でブレイクする。",
    "abilities": [
        {"kind": "static", "affects": "self",
         "mod": {"breaks": {"civ_count": {"zone": "bz", "owner": "opp"}}}},
    ],
    "source": {"official": "test-cc", "review": "pending"},
}


def test_civ_count_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    assert "civ_count" in ab["mod"]["breaks"]


def test_civ_count_in_cmp():
    card2 = {
        "id": "test-cc2",
        "name": "試験文明獣2",
        "types": ["creature"],
        "civs": ["water"],
        "cost": 4,
        "power": 4000,
        "races": ["テスト"],
        "text": "自分のマナゾーンにある文明が３種類以上なら、カードを１枚引く。",
        "abilities": [
            {"kind": "trigger",
             "when": {"event": "summon", "subject": "self"},
             "if": {"cmp": [{"civ_count": {"zone": "mana", "owner": "you"}}, ">=", 3]},
             "effect": [{"op": "draw", "count": 1}]},
        ],
        "source": {"official": "test-cc2", "review": "pending"},
    }
    parsed = parse_card(card2, TABLES)
    assert parsed is not None
