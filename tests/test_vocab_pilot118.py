"""語彙パイロット第118弾: summon_event_trigger（召喚した時）。

「自分の他のクリーチャーを召喚した時、〜」は move イベント
（to: bz, reason: summon）を他者 subject で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-set",
    "name": "試験召喚監視獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "自分の他のクリーチャーを召喚した時、カードを１枚引く。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz", "reason": "summon",
                  "subject": {"owner": "you", "other": True,
                              "filter": {"types": ["creature"]}}},
         "effect": [
             {"op": "draw", "count": 1},
         ]},
    ],
    "source": {"official": "test-set", "review": "pending"},
}


def test_summon_event_trigger_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"
    assert ab["when"]["reason"] == "summon"


def test_summon_event_subject_shape():
    card = parse_card(CARD, TABLES)
    subj = card.abilities[0]["when"]["subject"]
    assert subj["owner"] == "you"
    assert subj["other"] is True
