"""語彙パイロット第87弾: ultra_saber（ウルトラ・セイバー）。

「自分のメカまたはアーマードが離れる時、かわりにこのクリーチャーを破壊してもよい」は
replace（move from bz、optional、instead で self を破壊）で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-us",
    "name": "試験セイバー獣",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "自分のメカまたはアーマードが離れる時、かわりにこのクリーチャーを破壊してもよい。",
    "abilities": [
        {"kind": "replace",
         "when": {"event": "move", "from": "bz",
                  "subject": {"owner": "you", "other": True,
                              "filter": {"any_of": [{"race_has": "メカ"},
                                                    {"race_has": "アーマード"}]}}},
         "optional": True,
         "instead": [
             {"op": "destroy", "select": {"ref": "self"}},
         ]},
    ],
    "source": {"official": "test-us", "review": "pending"},
}


def test_ultra_saber_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "replace"
    assert ab["optional"] is True


def test_ultra_saber_subject():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["when"]["from"] == "bz"
    assert ab["when"]["subject"]["other"] is True
