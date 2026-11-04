"""語彙パイロット第50弾（フェーズ17）: 実カードの parse 確認。

対象: 《蔑如と覚悟》DM24RP3-076 — 「このターン、クリーチャーを1体、自分のマナゾーンから
召喚してもよい」が第50弾の回数制限つき許可（modify の allow に once）で表せるようになった。
マッハファイター付与は、マナゾーンからの召喚を待つ遅延誘発でそのクリーチャーに与える。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "dm24rp3-076",
    "name": "蔑如と覚悟",
    "types": ["spell"],
    "civs": ["nature"],
    "cost": 1,
    "mana": 1,
    "text": "このターン、クリーチャーを１体、自分のマナゾーンから召喚してもよい。そうしたら、このターン、そのクリーチャーに「マッハファイター」を与える。",
    "spell": [
        {"op": "modify",
         "select": {"zone": "mana", "owner": "you", "filter": {"types": ["creature"]}},
         "mod": {"allow": [{"action": "summon_from_mana", "once": True}]},
         "duration": "end_of_turn", "dynamic": True},
        {"op": "delayed_trigger",
         "when": {"event": "move", "from": "mana", "to": "bz", "reason": "summon",
                  "subject": {"owner": "you"}},
         "effect": [
             {"op": "modify", "select": {"ref": "subject"},
              "mod": {"allow": [{"action": "attack_creature", "other": {"tapped": False}}]},
              "duration": "end_of_turn"}]},
    ],
    "source": {"official": "dm24rp3-076", "review": "pending"},
}


def test_mana_summon_permission_spell_parses():
    card = parse_card(CARD, TABLES, where="dm24rp3-076")
    assert card.spell and len(card.spell) == 2
