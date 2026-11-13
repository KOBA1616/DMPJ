"""語彙パイロット第14弾: スマッシュ・バーストの代表カードの手変換が parse_card を通ること。

変換の型: クリーチャー面の攻撃時誘発に may + cast_face {face: 1} を置く。
"""
import pytest

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # ゲオルグ・バーボシュタイン / ゴースト・タッチ（相手が捨てた時の誘発もクリーチャー面にある）
        "id": "dm22ex2-005", "name": "ゲオルグ・バーボシュタイン / ゴースト・タッチ",
        "faces": [
            {"name": "ゲオルグ・バーボシュタイン", "types": ["creature"], "civs": ["darkness"],
             "cost": 4, "power": 3000, "races": ["マフィ・ギャング"],
             "abilities": [
                 {"kind": "trigger", "when": {"event": "attack", "subject": "self"},
                  "effect": [{"op": "may", "body": [{"op": "cast_face", "face": 1}]}]},
                 {"kind": "trigger",
                  "when": {"event": "move", "from": "hand", "to": "graveyard", "subject": {"owner": "opp"}},
                  "effect": [{"op": "modify",
                              "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}, "count": 1},
                              "mod": {"power": -3000}, "duration": "end_of_turn"}]},
             ]},
            {"name": "ゴースト・タッチ", "types": ["spell"], "civs": ["darkness"], "cost": 2,
             "spell": [{"op": "discard", "select": {"zone": "hand", "owner": "opp", "count": 1}}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_smash_burst_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
