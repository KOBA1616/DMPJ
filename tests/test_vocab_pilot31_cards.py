"""語彙パイロット第31弾: フェーズ9の代表カードの手変換が parse_card を通ること。

変換の型:
- フシギバース: 面の宣言 fushigi {cost, civs, min}
- ラスト・バースト: キーワード last_burst（ツインパクト）
- メテオバーン: キーワード meteor_burn
- ジャンケン: op janken {win, lose, draw}
- シールド・プラス: キーワード的な誘発 + op shield_plus
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # ライマー・チャント: フシギバース [自然9]（ETB部分は省略）
        "id": "dmex10-003", "name": "ライマー・チャント", "types": ["creature"], "civs": ["nature"],
        "cost": 9, "power": 9000, "keywords": ["double_breaker"],
        "fushigi": {"cost": 9, "civs": ["nature"], "min": 1},
    },
    {   # 第六戦街 ラヴ・ガトラー / インビンシブル・アビス: ラスト・バースト
        "id": "dm22ex1-099", "name": "第六戦街 ラヴ・ガトラー／インビンシブル・アビス",
        "faces": [
            {"name": "第六戦街 ラヴ・ガトラー", "types": ["creature"], "civs": ["darkness"],
             "cost": 7, "power": 7000, "keywords": ["blocker", "double_breaker", "last_burst"]},
            {"name": "インビンシブル・アビス", "types": ["spell"], "civs": ["darkness"], "cost": 6,
             "spell": [{"op": "discard", "select": {"zone": "hand", "owner": "opp", "count": 2}}]},
        ],
    },
    {   # 無敵巨兵スパルタンJ: メテオバーン
        "id": "dm23-001", "name": "無敵巨兵スパルタンJ", "types": ["creature", "evolution"], "civs": ["fire"],
        "cost": 7, "power": 8000, "keywords": ["blocker", "meteor_burn", "double_breaker"],
        "evolve_from": {"races": ["グレートメカオー"]},
    },
    {   # 鎧亜の魔術師グッチョッパ: ジャンケン
        "id": "dm26-019", "name": "鎧亜の魔術師グッチョッパ", "types": ["creature"], "civs": ["nature"],
        "cost": 4, "power": 4000, "enters_tapped_in_mana": True,
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "janken",
                  "win": [{"op": "may", "body": [{"op": "draw", "count": 3}]}],
                  "lose": [{"op": "discard", "select": {"zone": "hand", "owner": "you", "count": 1}}]}]},
        ],
    },
    {   # 幸せの精霊ミルザム・キッド: シールド・プラス
        "id": "dm26rp1-053", "name": "幸せの精霊ミルザム・キッド", "types": ["creature"], "civs": ["light"],
        "cost": 3, "power": 3000,
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "may", "body": [{"op": "shield_plus"}]}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_phase9_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
