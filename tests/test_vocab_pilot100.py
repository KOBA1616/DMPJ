"""語彙パイロット第100弾: oni_end（鬼エンド）。

「クリーチャーが攻撃する時、条件を満たせば手札からコストを支払わずに召喚してもよい」は
ニンジャ・ストライクと同じ declare（zone: hand）+ if 条件 + play_free で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-oni",
    "name": "試験鬼獣",
    "types": ["creature"],
    "civs": ["darkness", "fire"],
    "cost": 6,
    "power": 6000,
    "races": ["テスト"],
    "text": "鬼エンド：クリーチャーが攻撃する時、シールドが１つもないプレイヤーがいて、自分のマナゾーンに闇文明と火文明があれば、このクリーチャーを自分の手札からコストを支払わずに召喚してもよい。",
    "abilities": [
        {"kind": "declare",
         "zone": "hand",
         "when": {"event": "attack", "subject": {"owner": "any"}},
         "if": {"all": [
             {"any": [
                 {"cmp": [{"count": {"zone": "shield", "owner": "you"}}, "==", 0]},
                 {"cmp": [{"count": {"zone": "shield", "owner": "opp"}}, "==", 0]},
             ]},
             {"exists": {"zone": "mana", "owner": "you", "filter": {"civs": ["darkness"]}}},
             {"exists": {"zone": "mana", "owner": "you", "filter": {"civs": ["fire"]}}},
         ]},
         "effect": [
             {"op": "play_free", "select": {"ref": "self"}},
         ]},
    ],
    "source": {"official": "test-oni", "review": "pending"},
}


def test_oni_end_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "declare"
    assert ab["zone"] == "hand"


def test_oni_end_effect():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["effect"][0]["op"] == "play_free"
