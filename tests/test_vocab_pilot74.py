"""語彙パイロット第74弾: enters_event_trigger（他クリーチャーが出た時の誘発）。

「自分のジャイアントがバトルゾーンに出た時」は既存の when.subject セレクタで表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-eet",
    "name": "試験誘発獣",
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 3,
    "power": 3000,
    "races": ["テスト"],
    "text": "自分のジャイアントがバトルゾーンに出た時、このクリーチャーを自分のマナゾーンに置く。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz",
                  "subject": {"owner": "you", "other": True,
                              "filter": {"race_has": "ジャイアント"}}},
         "effect": [
             {"op": "move", "select": {"ref": "self"}, "to": "mana", "reason": "put"},
         ]},
    ],
    "source": {"official": "test-eet", "review": "pending"},
}


def test_enters_event_trigger_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"
    assert ab["when"]["subject"]["filter"]["race_has"] == "ジャイアント"


def test_enters_event_trigger_subject_owner():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["when"]["subject"]["owner"] == "you"
    assert ab["when"]["subject"]["other"] is True
