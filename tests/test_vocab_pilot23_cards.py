"""語彙パイロット第23弾: クリスタルアームズ（水晶武装）の代表カードの手変換が parse_card を通ること。

変換の型: マナを裏向きにする効果は op flip_down。「水晶武装N」は裏向きマナの枚数を
count（filter: face_down）で数える条件（if）で書き、常在型・誘発・コスト軽減に付ける。
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

FD2 = {"cmp": [{"count": {"zone": "mana", "owner": "you", "filter": {"face_down": True}}}, ">=", 2]}

CARDS = [
    {   # 終斗の親衛隊シウバ: 水晶武装2で自身がパワー+6000と W・ブレイカーを得る
        "id": "dm23ex3-071", "name": "終斗の親衛隊シウバ", "types": ["creature"], "civs": ["nature"],
        "cost": 2, "power": 2000, "races": ["オラクル・セレス", "ビーストフォーク"],
        "abilities": [
            {"kind": "static", "affects": "self", "if": FD2, "mod": {"power": 6000, "grant": ["double_breaker"]}},
        ],
    },
    {   # 悟りのクリス アラヤシキ: 出た時にマナを裏向きにしてもよい + 水晶武装2（出た時、2枚以上あれば2枚引く）
        "id": "dm24bd6-041", "name": "悟りのクリス アラヤシキ", "types": ["creature"], "civs": [],
        "cost": 3, "power": 1000, "races": ["オラクル・セレス"],
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "may", "body": [
                 {"op": "flip_down", "select": {"zone": "mana", "owner": "you", "count": 1}}]}]},
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"}, "if": FD2,
             "effect": [{"op": "draw", "count": 2}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_crystal_arms_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
