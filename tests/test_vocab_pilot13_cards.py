"""語彙パイロット第13弾: 代表カードの手変換が parse_card を通ること。

- 革命2（Rev.スパーク）: 条件は if の条件式で書き、成立時は「すべて」、不成立時は「1体」を else で分ける
- タップ燃料（助招!アルデ&パワッチ）: zone: hand の常在型に opt_reduce（do.tap）を置く
- 種族追加（お願い!デッキー）: mod add_races
"""
import pytest

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

REV = {"cmp": [{"count": {"zone": "shield", "owner": "you"}}, "<=", 2]}

CARDS = [
    {   # 革命2: 成立すれば相手すべてをタップ、しなければ1体
        "id": "dmr17-035", "name": "Rev.スパーク", "types": ["spell"], "civs": ["light"],
        "cost": 3, "keywords": ["s_trigger"],
        "spell": [
            {"op": "if", "cond": REV,
             "then": [{"op": "tap", "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}, "count": "all"}}],
             "else": [{"op": "tap", "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}, "count": 1}}]},
        ],
    },
    {   # 召喚時に自分のクリーチャーを1体タップして2軽減 + エスケープ
        "id": "dm23rp4x-027", "name": "助招!アルデ&パワッチ", "types": ["creature"], "civs": ["light"],
        "cost": 5, "power": 5500, "races": ["メカ・デル・ステラ", "アーマード・ファイアー・バード"],
        "keywords": ["escape"],
        "abilities": [
            {"kind": "static", "affects": "self", "zone": "hand",
             "mod": {"opt_reduce": {"amount": 2, "do": {
                 "select": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"], "tapped": False}},
                 "min": 1, "max": 1, "tap": True}}}},
        ],
    },
    {   # 自分のクリーチャーすべてに種族ジョーカーズを追加
        "id": "dmex19-039", "name": "お願い!デッキー", "types": ["creature"], "civs": ["zero"],
        "cost": 3, "power": 3000, "races": ["ジョーカーズ"],
        "abilities": [
            {"kind": "static", "affects": {"owner": "you", "filter": {"types": ["creature"]}},
             "mod": {"add_races": ["ジョーカーズ"]}},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_pilot13_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
