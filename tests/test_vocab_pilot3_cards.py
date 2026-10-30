"""語彙パイロット第3弾: rejects の代表カードの手変換が parse_card を通ること。

新規:
- dm37-037 マモ・ミステール … キーワード freeze（keywords.yaml に定義を追加）
- dm25rp4-056 ペナルティフリート … 効果内の choose フィルタは元々式が使えた（cost_gt_count）

第2弾までの語彙で表せるようになったもの:
- dmr19-028 ピッケス … 「そのターンはじめての攻撃」は first_time（first_attack_of_turn）＋ A型フリーズは tap の no_untap_next
- dmr16s-021 プロテクション・サークル … ゾーン枚数の比較は cmp の両辺に count 式（zone_count_comparison）
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # フリーズのみのクリーチャー
        "id": "dm37-037", "name": "仰天の守護者マモ・ミステール", "types": ["creature"], "civs": ["light"],
        "cost": 3, "power": 2000, "races": ["ガーディアン"], "mana": 1, "keywords": ["freeze"],
        "abilities": [],
    },
    {   # 自分のクリーチャーが攻撃する時、それがそのターンはじめての攻撃であれば、相手を1体タップして凍結する
        "id": "dmr19-028", "name": "煽動の翼 ピッケス", "types": ["creature"], "civs": ["light"],
        "cost": 4, "power": 3000, "races": ["ジャスティス・ウイング"], "mana": 1,
        "abilities": [
            {"kind": "trigger", "first_time": True,
             "when": {"event": "attack", "subject": {"owner": "you", "filter": {"types": ["creature"]}}},
             "effect": [
                 {"op": "choose", "select": {"zone": "bz", "owner": "opp",
                                             "filter": {"types": ["creature"]}, "count": 1}, "as": "tgt"},
                 {"op": "tap", "select": {"ref": "tgt"}, "no_untap_next": True}]},
        ],
    },
    {   # 自分の手札を1枚シールドに加える。自分のシールドが相手より多ければ1枚引いてもよい
        "id": "dmr16s-021", "name": "プロテクション・サークル", "types": ["spell"], "civs": ["light"],
        "cost": 3, "mana": 1,
        "spell": [
            {"op": "move", "select": {"zone": "hand", "owner": "you", "count": 1},
             "to": "shield", "reason": "put"},
            {"op": "if", "cond": {"cmp": [{"count": {"zone": "shield", "owner": "you"}}, ">",
                                          {"count": {"zone": "shield", "owner": "opp"}}]},
             "then": [{"op": "may", "body": [{"op": "draw", "count": 1}]}]},
        ],
    },
    {   # 出た時、相手のマナ枚数よりコストが大きい相手クリーチャーを1体選び、持ち主の山札の下に置く
        "id": "dm25rp4-056", "name": "星姫械 ペナルティフリート", "types": ["creature"], "civs": ["light"],
        "cost": 4, "power": 4500, "races": ["メカ・デル・ステラ"], "mana": 1,
        "keywords": ["s_trigger", "blocker"],
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "choose",
                  "select": {"zone": "bz", "owner": "opp",
                             "filter": {"types": ["creature"],
                                        "cost_ge": {"sum": [{"count": {"zone": "mana", "owner": "opp"}}, 1]}},
                             "count": 1},
                  "as": "tgt"},
                 {"op": "move", "select": {"ref": "tgt"}, "to": "deck", "reason": "return",
                  "position": "bottom"}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_representative_reject_now_parses3(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
