"""語彙パイロット第106弾: trigger_when_wins_battle（バトルに勝った時）。

「このクリーチャーがバトルに勝った時、〜」は既存の battle_win イベント
（勝者のみ subject）で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-twwb",
    "name": "試験凱旋獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 5,
    "power": 5000,
    "races": ["テスト"],
    "text": "このクリーチャーがバトルに勝った時、カードを１枚引く。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "battle_win", "subject": "self"},
         "effect": [
             {"op": "draw", "count": 1},
         ]},
    ],
    "source": {"official": "test-twwb", "review": "pending"},
}


def test_battle_win_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"


def test_battle_win_when():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["when"]["event"] == "battle_win"
    assert ab["when"]["subject"] == "self"
