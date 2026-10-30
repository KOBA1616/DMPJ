"""語彙パイロット第11弾: キリフダッシュの代表カードの手変換が parse_card を通ること。

変換の型: 手札で機能する誘発（zone: hand）で attack_end を受け、when の broke: true で
「その攻撃中にブレイクした」ことを指定する。効果は may + play_self（代替コスト）。
[XYnn] の nn が総額、XY が必要な文明（[cc00] はコスト0＝文明指定なし）。
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()


def kirifudash(cost, civs):
    return {"kind": "trigger", "zone": "hand", "optional": True,
            "when": {"event": "attack_end", "broke": True, "subject": {"owner": "you"}},
            "effect": [{"op": "may", "body": [{"op": "play_self", "cost": cost, "civs": civs}]}]}


CARDS = [
    {   # キリフダッシュ[コスト0]。マナに火と自然がなければ攻撃できない
        "id": "dm24ex2-100", "name": "キタカゼマンA", "types": ["creature"], "civs": ["fire", "nature"],
        "cost": 2, "power": 2000, "races": ["ジョーカーズ", "チーム切札"], "mana": 1,
        "abilities": [
            kirifudash(0, []),
            {"kind": "static", "affects": "self",
             "if": {"not": {"all": [
                 {"exists": {"zone": "mana", "owner": "you", "filter": {"civs": ["fire"]}}},
                 {"exists": {"zone": "mana", "owner": "you", "filter": {"civs": ["nature"]}}}]}},
             "mod": {"deny": ["attack_player", "attack_creature"]}},
        ],
    },
    {   # キリフダッシュ[自然1]。ウェーブストライカー（他に2体以上でマッハファイターを得る）
        "id": "dm22ex1-125", "name": "ゲキオコ・マロン", "types": ["creature"], "civs": ["nature"],
        "cost": 3, "power": 4000, "races": ["ワイルド・ベジーズ"], "mana": 1,
        "keywords": ["wave_striker"],
        "abilities": [
            kirifudash(1, ["nature"]),
            {"kind": "static", "affects": "self",
             "if": {"cmp": [{"count": {"zone": "bz", "owner": "you", "other": True,
                                        "filter": {"keyword": "wave_striker"}}}, ">=", 2]},
             "mod": {"allow": [{"action": "attack_creature", "other": {"tapped": False}}]}},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_kirifudash_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
