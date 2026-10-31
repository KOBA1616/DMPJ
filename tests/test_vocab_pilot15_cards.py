"""語彙パイロット第15弾: ギャラクシールドの代表カードの手変換が parse_card を通ること。

変換の型: 面に galaxy_shield {cost, civs} を宣言し、ターン開始時の召喚は zone: shield の
誘発（条件 face_up）に summon_self を置く。表向きで置かれた時の誘発は when の face_up: true。
手札を表向きにシールド化する効果は move の face_up: true。
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # 「正義全帝」: GS [lw06] + 置いた時3ドロー + ターン開始時召喚 + 出た時、手札を表向きにシールド化
        "id": "dm22ex1-016", "name": "「正義全帝」", "types": ["creature"], "civs": ["light", "water"],
        "cost": 8, "power": 15000, "races": ["メタリカ", "チーム銀河"], "mana": 1,
        "keywords": ["g_strike", "triple_breaker"],
        "galaxy_shield": {"cost": 6, "civs": ["light", "water"]},
        "abilities": [
            {"kind": "trigger", "zone": "shield", "when": {"event": "turn_start", "player": "you"},
             "if": {"face_up": True}, "effect": [{"op": "summon_self"}]},
            {"kind": "trigger", "zone": "shield",
             "when": {"event": "move", "to": "shield", "subject": "self", "face_up": True},
             "effect": [{"op": "may", "body": [{"op": "draw", "count": 3}]}]},
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "move",
                         "select": {"zone": "hand", "owner": "you", "count": {"max": 99}},
                         "to": "shield", "reason": "put", "face_up": True}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_galaxyshield_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
