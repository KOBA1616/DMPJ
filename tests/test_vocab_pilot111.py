"""語彙パイロット第111弾: optional_enters_tapped（タップして出てもよい）。

「このクリーチャーはタップして出てもよい。そうした場合、カードを1枚引く」は
出現置換（replace/move→bz）の may で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-oet",
    "name": "試験臥待獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "このクリーチャーはタップして出てもよい。そうした場合、カードを1枚引く。",
    "abilities": [
        {"kind": "replace",
         "when": {"event": "move", "subject": "self", "to": "bz"},
         "optional": True,
         "effect": [
             {"op": "tap", "select": {"ref": "self"}},
             {"op": "draw", "count": 1},
         ]},
    ],
    "source": {"official": "test-oet", "review": "pending"},
}


def test_optional_tapped_replace_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "replace"
    assert ab["optional"] is True


def test_optional_tapped_effect_shape():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["effect"][0] == {"op": "tap", "select": {"ref": "self"}}
