"""語彙パイロット第8弾: メクレイドの代表カードの手変換が parse_card を通ること。

「X・メクレイドN」は `{op: mekurade, filter: {race_has: X}, cost_le: N}`。
対象が種族でなくタイプや文明のこともある（filter の通常のキーで表す）。
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # 自分のメカを1つタップしてもよい。そうしたら、メカ・メクレイド5する
        "id": "dm25ex1-076", "name": "聖沌忍法 b4ckd00r", "types": ["spell"], "civs": ["light"],
        "cost": 3, "mana": 1,
        "spell": [
            {"op": "may", "body": [
                {"op": "choose", "select": {"zone": "bz", "owner": "you",
                                            "filter": {"types": ["creature"], "race_has": "メカ"}, "count": 1},
                 "as": "t"}]},
            {"op": "if", "cond": {"exists": {"ref": "t"}}, "then": [
                {"op": "tap", "select": {"ref": "t"}},
                {"op": "mekurade", "filter": {"race_has": "メカ"}, "cost_le": 5}]},
        ],
    },
    {   # 攻撃する時、ドリームメイト・メクレイド5する（マッハファイターは展開形）
        "id": "dm24ex1-014", "name": "龍后幻獣パティシエ・メイ様", "types": ["creature"],
        "civs": ["light", "fire", "nature"], "cost": 5, "power": 6000, "mana": 1,
        "races": ["ドリームメイト", "ドラゴンの花嫁"],
        "keywords": ["speed_attacker", "double_breaker", "escape"],
        "abilities": [
            {"kind": "static", "affects": "self",
             "mod": {"allow": [{"action": "attack_creature", "other": {"tapped": False}}]}},
            {"kind": "trigger", "when": {"event": "attack", "subject": "self"},
             "effect": [{"op": "mekurade", "filter": {"race_has": "ドリームメイト"}, "cost_le": 5}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_mekurade_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
