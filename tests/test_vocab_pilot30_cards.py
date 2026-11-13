"""語彙パイロット第30弾: フェーズ8の代表カードの手変換が parse_card を通ること。

変換の型:
- ビビッドロー: 面の宣言 vividraw {cost, civs}
- 強制攻撃: キーワード must_attack
- 究極進化: evolve_from {types: [evolution]}
"""
import pytest

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # 翔天 スケプ-3: ビビッドロー [水火2]（他の能力は省略）
        "id": "dm26rp3-049", "name": "翔天 スケプ-3", "types": ["creature"], "civs": ["water", "fire"],
        "cost": 4, "power": 4000, "vividraw": {"cost": 2, "civs": ["water", "fire"]},
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "draw", "count": 4},
                 {"op": "move", "select": {"zone": "hand", "owner": "you", "count": 2},
                  "to": "deck", "reason": "put", "position": "top"}]},
        ],
    },
    {   # 凶戦士ブレイズ・クロー: 強制攻撃のみ
        "id": "dm24ex4-094", "name": "凶戦士ブレイズ・クロー", "types": ["creature"], "civs": ["fire"],
        "cost": 1, "power": 1000, "keywords": ["must_attack"],
    },
    {   # 神羅サンダー・ムーン: 究極進化
        "id": "dm23ex2-006", "name": "神羅サンダー・ムーン", "types": ["creature", "evolution"], "civs": ["nature"],
        "cost": 9, "power": 13000, "keywords": ["triple_breaker"],
        "evolve_from": {"types": ["evolution"]},
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "may", "body": [
                     {"op": "play_free", "select": {"zone": "mana", "owner": "you", "count": 1,
                                                     "filter": {"types": ["spell"]}}}]}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_phase8_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
