"""語彙パイロット第22弾: クロスギアの代表カードの手変換が parse_card を通ること。

変換の型: クロスギア本体は types: [cross_gear]。クロスしたクリーチャーへの効果は
affects: crossed（常在型）/ subject: crossed（誘発）で書く。クロスギアを出す効果は通常の move。
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # 炎刃 イダテン・アクセラー: クロスしたクリーチャーにスピードアタッカーを与える
        "id": "dm23ex1-079", "name": "炎刃 イダテン・アクセラー", "types": ["cross_gear"], "civs": ["fire"],
        "cost": 1, "races": ["サムライ"],
        "abilities": [
            {"kind": "static", "affects": "crossed", "mod": {"grant": ["speed_attacker"]}},
        ],
    },
    {   # 神影剣士ジュウベイ: S・トリガー + 出た時、手札のクロスギアを1枚出してもよい（超次元ゾーン分は対象外フォーマット）
        "id": "dm22ex1-114", "name": "神影剣士ジュウベイ", "types": ["creature"], "civs": ["fire"],
        "cost": 5, "power": 5000, "races": ["ヒューマノイド", "サムライ"],
        "keywords": ["s_trigger"],
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "may", "body": [
                 {"op": "move", "select": {"zone": "hand", "owner": "you", "filter": {"types": ["cross_gear"]}, "count": 1},
                  "to": "bz", "reason": "put"}]}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_cross_gear_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
