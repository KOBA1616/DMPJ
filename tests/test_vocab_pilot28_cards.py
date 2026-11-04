"""語彙パイロット第28弾: フェーズ6の代表カードの手変換が parse_card を通ること。

変換の型:
- アバレチェーン: first_time + 攻撃誘発（自分のクリーチャー）+ may の else
- ヨビニオン: キーワード yobinion
- オシオキムーン: 自分のシールドが離れた時の誘発（when の from: shield + subject owner: you）
- マナゾーンから召喚: キーワード summon_from_mana
- シンカパワー: when に stacked: true
- 進化ではない: フィルタの not_types
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # 魔軸の鎖 カメカメン: アバレチェーン
        "id": "dm25ex3-rp2tr7", "name": "魔軸の鎖 カメカメン", "types": ["creature"], "civs": ["light"],
        "cost": 3, "power": 3000,
        "abilities": [
            {"kind": "trigger", "first_time": True,
             "when": {"event": "attack", "subject": {"owner": "you", "filter": {"types": ["creature"]}}},
             "effect": [
                 {"op": "may", "body": [
                     {"op": "play_free", "select": {"zone": "hand", "owner": "you", "count": 1,
                                                     "filter": {"types": ["spell"], "cost_le": 4}}}],
                  "else": [{"op": "draw", "count": 1}]}]},
        ],
    },
    {   # 八卦ヨーイ: ヨビニオン
        "id": "dm24bd2-012", "name": "八卦ヨーイ", "types": ["creature"], "civs": [],
        "cost": 4, "power": 5000, "keywords": ["yobinion"],
    },
    {   # 月と破壊と魔王と天使: オシオキムーン（自分のシールドが離れた時、相手のシールドを1つブレイクしてもよい）
        "id": "dm24ex4-003", "name": "月と破壊と魔王と天使", "types": ["creature"], "civs": ["light", "darkness"],
        "cost": 7, "power": 11500, "keywords": ["blocker", "double_breaker"],
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "move", "select": {"zone": "deck", "owner": "you", "count": 2}, "to": "shield", "reason": "put"}]},
            {"kind": "trigger", "when": {"event": "move", "from": "shield", "subject": {"owner": "you"}},
             "effect": [{"op": "may", "body": [{"op": "break", "count": 1}]}]},
        ],
    },
    {   # 大冒犬ヤッタルツー: マナゾーンから召喚 + タップした時マナに置く
        "id": "dm24rp2-073", "name": "大冒犬ヤッタルツー", "types": ["creature"], "civs": ["nature"],
        "cost": 2, "power": 2000, "keywords": ["summon_from_mana"],
        "abilities": [
            {"kind": "trigger", "when": {"event": "tap", "subject": "self"},
             "effect": [{"op": "move", "select": {"ref": "self"}, "to": "mana", "reason": "charge", "tapped": True}]},
        ],
    },
    {   # ネ申・マニフェスト: シンカパワー（進化する時）
        "id": "dm22ex1-026", "name": "ネ申・マニフェスト", "types": ["creature"], "civs": ["water"],
        "cost": 3, "power": 2000,
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "draw", "count": 3},
                 {"op": "discard", "select": {"zone": "hand", "owner": "you", "count": 2}}]},
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self", "stacked": True},
             "effect": [
                 {"op": "modify", "select": {"ref": "self"}, "mod": {"deny": ["be_blocked"]},
                  "duration": "until_next_own_turn_start"}]},
        ],
    },
    {   # 赤薔薇の精霊龍 ジェネラローズ: 進化ではないクリーチャーを出す
        "id": "dm25ex1-036", "name": "赤薔薇の精霊龍 ジェネラローズ", "types": ["creature"], "civs": ["light"],
        "cost": 7, "power": 7500, "keywords": ["double_breaker"],
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "draw", "count": 1},
                 {"op": "may", "body": [
                     {"op": "move", "select": {"zone": "hand", "owner": "you", "count": 1,
                                                "filter": {"types": ["creature"], "not_types": ["evolution"],
                                                           "cost_le": 6, "civs": ["light"]}},
                      "to": "bz", "reason": "put"}]}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_phase6_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
