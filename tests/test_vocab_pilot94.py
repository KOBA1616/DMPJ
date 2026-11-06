"""語彙パイロット第94弾: entry_replacement（出る時の置換）。

「相手のクリーチャーが出る時、かわりに墓地に置く」は replace（move to bz）で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-er",
    "name": "試験門番獣",
    "types": ["creature"],
    "civs": ["darkness"],
    "cost": 6,
    "power": 5000,
    "races": ["テスト"],
    "text": "自分のターンに相手のクリーチャーが出る時、かわりにそのクリーチャーを墓地に置く。",
    "abilities": [
        {"kind": "replace",
         "when": {"event": "move", "to": "bz",
                  "subject": {"owner": "opp", "filter": {"types": ["creature"]}}},
         "if": {"is_turn": "you"},
         "instead": [
             {"op": "move", "select": {"ref": "event.subject"}, "to": "graveyard", "reason": "put"},
         ]},
    ],
    "source": {"official": "test-er", "review": "pending"},
}


def test_entry_replacement_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "replace"


def test_entry_replacement_when():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["when"]["to"] == "bz"
    assert ab["when"]["subject"]["owner"] == "opp"
