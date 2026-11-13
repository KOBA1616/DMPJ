"""語彙パイロット第7弾: 鬼タイム「真上の▪️能力を無視する」の代表カードの手変換が parse_card を通ること。

無視したい能力には id を付け（変換では真上の能力に付ける）、鬼タイムの常在型が
mod {ignore_ids: [その id]} を持つ。キーワード由来の能力を無視したい場合は、
キーワードの展開形を id つきで直接書く（アシガル変怪の「攻撃できない」）。
"""
import pytest

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()
ONI = {"cmp": [{"sum": [{"count": {"zone": "shield", "owner": "you"}},
                        {"count": {"zone": "shield", "owner": "opp"}}]}, "<=", 6]}

CARDS = [
    {   # 攻撃できない（真上）。鬼タイムで無視する
        "id": "dmrp14-079", "name": "アシガル変怪", "types": ["creature"], "civs": ["fire"],
        "cost": 1, "power": 2000, "races": ["ドラゴノイド", "鬼札王国"], "mana": 1,
        "abilities": [
            {"kind": "static", "id": "above", "affects": "self",
             "mod": {"deny": ["attack_player", "attack_creature"]}},
            {"kind": "static", "affects": "self", "if": ONI, "mod": {"ignore_ids": ["above"]}},
        ],
    },
    {   # 各ターンの終わりに、タップしていれば破壊する（真上）。鬼タイムで無視する
        "id": "dmrp14-054", "name": "キリツケ入道", "types": ["creature"], "civs": ["darkness", "fire"],
        "cost": 3, "power": 5000, "races": ["ブレイブ・スピリット", "鬼札王国"], "mana": 1,
        "keywords": ["blocker", "speed_attacker"],
        "abilities": [
            {"kind": "trigger", "id": "above", "when": {"event": "turn_end"},
             "if": {"exists": {"ref": "self", "filter": {"tapped": True}}},
             "effect": [{"op": "destroy", "select": {"ref": "self"}}]},
            {"kind": "static", "affects": "self", "if": ONI, "mod": {"ignore_ids": ["above"]}},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_ignore_ids_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
