"""語彙パイロット第119弾: enters_non_summon（召喚以外の方法で出た時）。

「相手のターン中に、相手のクリーチャーが召喚以外の方法で出た時」は
move イベント（to: bz, reason: put）の誘発で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-ens",
    "name": "試験異端流獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 3,
    "power": 2000,
    "races": ["テスト"],
    "text": "相手のターン中に、相手のクリーチャーが召喚以外の方法で出た時、そのクリーチャーを破壊する。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz", "reason": "put",
                  "subject": {"owner": "opp", "filter": {"types": ["creature"]}}},
         "if": {"is_turn": "opp"},
         "effect": [
             {"op": "destroy", "select": {"ref": "event.subject"}},
         ]},
    ],
    "source": {"official": "test-ens", "review": "pending"},
}


def test_non_summon_trigger_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"
    assert ab["when"]["reason"] == "put"


def test_non_summon_subject_shape():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["when"]["subject"]["owner"] == "opp"
    assert ab["if"] == {"is_turn": "opp"}
