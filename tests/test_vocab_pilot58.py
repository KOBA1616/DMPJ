"""語彙パイロット第58弾: マッハファイターの付与パターン。

「〜に『マッハファイター』を与える」は op: modify で
mod: {allow: [{action: attack_creature, other: {tapped: false}}]} を
duration: end_of_turn で付与する（第50弾の dm24rp3-076 が先例）。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

# 誘発型付与: 自分のコスト6以上のクリーチャーが出た時、そのクリーチャーに与える
TRIGGER_GRANT = {
    "id": "test-mf-trigger",
    "name": "試験付与獣",
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 2,
    "power": 2000,
    "races": ["テスト"],
    "text": "自分のコスト６以上のクリーチャーが出た時、このターン、そのクリーチャーに「マッハファイター」を与える。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz",
                  "subject": {"owner": "you", "filter": {"types": ["creature"], "cost_ge": 6}}},
         "effect": [
             {"op": "modify", "select": {"ref": "event.subject"},
              "mod": {"allow": [{"action": "attack_creature", "other": {"tapped": False}}]},
              "duration": "end_of_turn"}]},
    ],
    "source": {"official": "test-mf-trigger", "review": "pending"},
}

# 常在型付与: 自分のクリーチャーすべてに与える
STATIC_GRANT = {
    "id": "test-mf-static",
    "name": "試験全体付与獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 5,
    "power": 5000,
    "races": ["テスト"],
    "text": "自分のクリーチャーすべてに「マッハファイター」を与える。",
    "abilities": [
        {"kind": "static",
         "affects": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"]}},
         "mod": {"gain": [
             {"kind": "trigger",
              "when": {"event": "move", "to": "bz", "subject": "self"},
              "effect": [
                  {"op": "modify", "select": {"ref": "self"},
                   "mod": {"allow": [{"action": "attack_creature", "other": {"tapped": False}}]},
                   "duration": "end_of_turn"}]}]}},
    ],
    "source": {"official": "test-mf-static", "review": "pending"},
}


def test_trigger_grant_parses():
    card = parse_card(TRIGGER_GRANT, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"
    mod = ab["effect"][0]["mod"]
    allow = mod["allow"][0]
    assert allow["action"] == "attack_creature"
    assert allow["other"]["tapped"] is False
    assert ab["effect"][0]["duration"] == "end_of_turn"


def test_static_grant_parses():
    card = parse_card(STATIC_GRANT, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    gained = ab["mod"]["gain"][0]
    assert gained["kind"] == "trigger"
    mod = gained["effect"][0]["mod"]
    allow = mod["allow"][0]
    assert allow["action"] == "attack_creature"
    assert allow["other"]["tapped"] is False
