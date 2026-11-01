"""語彙パイロット第29弾: フェーズ7の代表カードの手変換が parse_card を通ること。

変換の型:
- 進化V: evolve_from をフィルタのリストにする
- 代替コスト（別額）: 面の宣言 alt_cost {cost, civs} + 条件式 {alt_paid: true}
- 代替コスト（行動）: 面の宣言 alt_cost {do: [...]}
- 進化クリーチャーを数える/参照する: count 式とフィルタの types（既存）
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # 霊流星バルファート: 進化V（光+自然）。破壊時の身代わりは置換で別途（ここでは進化Vの宣言のみ検証）
        "id": "dm24-007", "name": "霊流星バルファート", "types": ["creature", "evolution"], "civs": ["light", "nature"],
        "cost": 8, "power": 8000, "keywords": ["double_breaker"],
        "evolve_from": [{"civs": ["light"]}, {"civs": ["nature"]}],
        "enters_tapped_in_mana": True,
    },
    {   # ペダンティック・ガード: 代替コスト [光光4] + そうしたら相手がシールド化してもよい
        "id": "dm26ex4-043", "name": "ペダンティック・ガード", "types": ["spell"], "civs": ["light"], "cost": 5,
        "alt_cost": {"cost": 4, "civs": ["light", "light"]},
        "spell": [
            {"op": "if", "cond": {"alt_paid": True}, "then": [
                {"op": "opp_may", "body": [
                    {"op": "move", "select": {"zone": "deck", "owner": "you", "count": 1}, "to": "shield", "reason": "put"}]}]},
            {"op": "move", "select": {"zone": "deck", "owner": "you", "count": 2}, "to": "shield", "reason": "put"},
        ],
    },
    {   # 闇王ゼーロ: 代替コスト（行動）= 闇のカード3枚捨て + 自分の闇クリーチャー3体破壊
        "id": "dm26ex3-031", "name": "闇王ゼーロ", "types": ["spell"], "civs": ["darkness"], "cost": 8,
        "alt_cost": {"do": [
            {"zone": "hand", "filter": {"civs": ["darkness"]}, "count": 3, "to": "graveyard", "reason": "discard"},
            {"zone": "bz", "filter": {"types": ["creature"], "civs": ["darkness"]}, "count": 3, "to": "graveyard", "reason": "destroy"},
        ]},
        "spell": [
            {"op": "move", "select": {"zone": "deck", "owner": "you", "count": 4}, "to": "graveyard", "reason": "put"},
            {"op": "move", "select": {"zone": "graveyard", "owner": "you", "count": 1,
                                        "filter": {"types": ["creature"], "civs": ["darkness"]}},
             "to": "bz", "reason": "put"},
        ],
    },
    {   # 借魂: 「自分の進化クリーチャー1体につき1枚引く」= count 式（既存）
        "id": "dm25rp1-031", "name": "借魂", "types": ["spell"], "civs": ["darkness"], "cost": 2,
        "keywords": ["g_strike"],
        "spell": [
            {"op": "draw", "count": {"count": {"zone": "bz", "owner": "you", "filter": {"types": ["evolution"]}}}},
        ],
    },
    {   # 歓喜老GO-GEKI-63: 「自分の進化クリーチャーがなければ攻撃できない」（既存の条件つき常在型）
        "id": "dm25rp4-046", "name": "歓喜老GO-GEKI-63", "types": ["creature"], "civs": ["fire"],
        "cost": 6, "power": 9000, "keywords": ["triple_breaker"],
        "abilities": [
            {"kind": "static", "affects": "self",
             "if": {"cmp": [{"count": {"zone": "bz", "owner": "you", "filter": {"types": ["evolution"]}}}, "==", 0]},
             "mod": {"deny": ["attack_player", "attack_creature"]}},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_phase7_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
