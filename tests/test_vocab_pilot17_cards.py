"""語彙パイロット第17弾: NEO進化の代表カードの手変換が parse_card を通ること。

変換の型: 面に neo: true と evolve_from を置く（types に evolution は入れない）。
「NEO進化クリーチャーなら」は、自身を types: [evolution] で見る exists 条件で書く。
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

NEO = {"exists": {"ref": "self", "filter": {"types": ["evolution"]}}}

CARDS = [
    {   # 死神明王 XENIA: NEO進化（闇）+ 出た時、それがNEO進化なら闇以外すべてを破壊 + 攻撃時、墓地から闇を出す
        "id": "dm22ex1-027", "name": "死神明王 XENIA", "types": ["creature"], "civs": ["darkness"],
        "cost": 8, "power": 12000, "races": ["デーモン・コマンド"],
        "keywords": ["triple_breaker"],
        "neo": True, "evolve_from": {"civs": ["darkness"]},
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"}, "if": NEO,
             "effect": [{"op": "destroy",
                         "select": {"zone": "bz", "owner": "any", "filter": {"types": ["creature"], "not_civs": ["darkness"]}, "count": "all"}}]},
            {"kind": "trigger", "when": {"event": "attack", "subject": "self"},
             "effect": [{"op": "may", "body": [
                 {"op": "move",
                  "select": {"zone": "graveyard", "owner": "you", "filter": {"types": ["creature"], "civs": ["darkness"]}, "count": 1},
                  "to": "bz", "reason": "put"}]}]},
        ],
    },
    {   # ボルシャック・ヤング・ドラゴン: NEO進化（火）+ パワード・ブレイカー + 攻撃中、墓地の火1枚につき+1000
        "id": "dm24ex2-068", "name": "ボルシャック・ヤング・ドラゴン", "types": ["creature"], "civs": ["fire"],
        "cost": 4, "power": 6000, "races": ["アーマード・ドラゴン"],
        "keywords": ["powered_breaker"],
        "neo": True, "evolve_from": {"civs": ["fire"]},
        "abilities": [
            {"kind": "static", "affects": "self",
             "mod": {"battle_power": {"amount": 1000, "count": {"zone": "graveyard", "owner": "you", "filter": {"civs": ["fire"]}}}}},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_neo_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
