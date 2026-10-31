"""語彙パイロット第18弾: スター進化の代表カードの手変換が parse_card を通ること。

変換の型: types に evolution を含め、star: true と evolve_from を置く。
進化元が「レクスターズまたは〈文明〉」の OR 条件は、filter の any_of で書く（第18弾で追加）。
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # 「正義星帝」 ＜鬼羅.Star＞: スター進化（レクスターズ/光）+ 出た時/攻撃時ドローしてコスト4以下を出す
        "id": "dm22bd2-005", "name": "「正義星帝」 ＜鬼羅.Star＞", "types": ["creature", "evolution"],
        "civs": ["light"], "cost": 5, "power": 8500,
        "races": ["メタリカ", "ヒューマノイド", "レクスターズ"],
        "keywords": ["double_breaker"],
        "star": True,
        "evolve_from": {"any_of": [{"race_has": "レクスターズ"}, {"civs": ["light"]}]},
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "draw", "count": 1},
                 {"op": "may", "body": [
                     {"op": "move", "select": {"zone": "hand", "owner": "you", "filter": {"types": ["creature"], "cost_le": 4}, "count": 1},
                      "to": "bz", "reason": "put"}]}]},
            {"kind": "static",
             "affects": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"], "cost_le": 4}},
             "mod": {"grant": ["blocker"]}},
        ],
    },
    {   # オンソク童子 ＜ターボ.鬼＞: スター進化（レクスターズ/火）+ 出た時、手札を1枚捨てて1枚引く（タマシード進化ならもう1枚）
        "id": "dm23ex2-099", "name": "オンソク童子 ＜ターボ.鬼＞", "types": ["creature", "evolution"],
        "civs": ["fire"], "cost": 2, "power": 4000,
        "races": ["ソニック・コマンド", "鬼レクスターズ"],
        "star": True,
        "evolve_from": {"any_of": [{"race_has": "レクスターズ"}, {"civs": ["fire"]}]},
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "move", "select": {"zone": "hand", "owner": "you", "count": 1}, "to": "graveyard", "reason": "discard"},
                 {"op": "draw", "count": 1},
             ]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_star_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
