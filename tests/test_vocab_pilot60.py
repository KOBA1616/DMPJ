"""語彙パイロット第60弾: attack_untapped（アンタップしているクリーチャーを攻撃できる）。

マッハファイターの効果部分と同じ語彙（第58弾）。
違いは「出たターンの間」の制限が無い点。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-au",
    "name": "試験攻撃獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 4,
    "power": 4000,
    "races": ["テスト"],
    "text": "このクリーチャーは、アンタップしているクリーチャーを攻撃できる。",
    "abilities": [
        {"kind": "static", "affects": "self",
         "mod": {"allow": [{"action": "attack_creature", "other": {"tapped": False}}]}},
    ],
    "source": {"official": "test-au", "review": "pending"},
}

GRANT = {
    "id": "test-au-grant",
    "name": "試験付与獣",
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 3,
    "power": 3000,
    "races": ["テスト"],
    "text": "このクリーチャーがバトルゾーンに出た時、そのターン、自分のクリーチャー１体は、アンタップしているクリーチャーを攻撃できる。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz", "subject": "self"},
         "effect": [
             {"op": "choose", "select": {"zone": "bz", "owner": "you",
                                         "filter": {"types": ["creature"]}, "count": 1},
              "as": "target"},
             {"op": "modify", "select": {"ref": "target"},
              "mod": {"allow": [{"action": "attack_creature", "other": {"tapped": False}}]},
              "duration": "end_of_turn"},
         ]},
    ],
    "source": {"official": "test-au-grant", "review": "pending"},
}


def test_attack_untapped_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    allow = ab["mod"]["allow"][0]
    assert allow["action"] == "attack_creature"
    assert allow["other"]["tapped"] is False


def test_attack_untapped_grant_parses():
    card = parse_card(GRANT, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"
    mod = ab["effect"][1]["mod"]
    allow = mod["allow"][0]
    assert allow["action"] == "attack_creature"
    assert allow["other"]["tapped"] is False
