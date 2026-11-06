"""語彙パイロット第99弾: attack_target_filter（攻撃できる対象のフィルタ）。

「タップされていない光のクリーチャーを攻撃できる」は第60弾の allow に
other フィルタ（civs 等）を付けて表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-atf",
    "name": "試験狩人獣",
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "このクリーチャーは、タップされていない光のクリーチャーを攻撃できる。",
    "abilities": [
        {"kind": "static", "affects": "self",
         "mod": {"allow": [{"action": "attack_creature",
                            "other": {"tapped": False, "civs": ["light"]}}]}},
    ],
    "source": {"official": "test-atf", "review": "pending"},
}


def test_attack_target_filter_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"


def test_attack_target_filter_other():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    allow = ab["mod"]["allow"][0]
    assert allow["action"] == "attack_creature"
    assert allow["other"]["civs"] == ["light"]
    assert allow["other"]["tapped"] is False
