"""語彙パイロット第104弾: attack_end_trigger（攻撃の終わりに）。

「このクリーチャーの攻撃の終わりに、〜」は既存の attack_end イベント
（攻撃クリーチャーが subject）で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-aet",
    "name": "試験再起獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 5,
    "power": 5000,
    "races": ["テスト"],
    "text": "このクリーチャーの攻撃の終わりに、このクリーチャーをアンタップする。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "attack_end", "subject": "self"},
         "effect": [
             {"op": "untap", "select": {"ref": "self"}},
         ]},
    ],
    "source": {"official": "test-aet", "review": "pending"},
}


def test_attack_end_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"


def test_attack_end_when():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["when"]["event"] == "attack_end"
    assert ab["when"]["subject"] == "self"
