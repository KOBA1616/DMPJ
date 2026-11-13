"""語彙パイロット第139弾: mach_fighter_grant（マッハファイターの付与）。

「そのクリーチャーにマッハファイターを与える」は modify の
mod: {allow: [{action: attack_creature, other: {tapped: false}}]}（第58弾の展開形）。
新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-mfg",
    "name": "試験速攻付与獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "自分のコスト６以上のクリーチャーが出た時、そのターン、そのクリーチャーに「マッハファイター」を与える。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz",
                  "subject": {"owner": "you", "other": True,
                              "filter": {"types": ["creature"], "cost_ge": 6}}},
         "effect": [
             {"op": "modify",
              "select": {"ref": "event.subject"},
              "mod": {"allow": [{"action": "attack_creature", "other": {"tapped": False}}]},
              "duration": "end_of_turn"},
         ]},
    ],
    "source": {"official": "test-mfg", "review": "pending"},
}


def test_mach_fighter_grant_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    assert card.abilities[0]["kind"] == "trigger"


def test_mach_fighter_grant_shape():
    card = parse_card(CARD, TABLES)
    mod = card.abilities[0]["effect"][0]["mod"]
    assert mod["allow"][0]["action"] == "attack_creature"
    assert mod["allow"][0]["other"] == {"tapped": False}
