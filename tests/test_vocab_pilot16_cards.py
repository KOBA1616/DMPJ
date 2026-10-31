"""語彙パイロット第16弾: ゴッドリンクの代表カードの手変換が parse_card を通ること。

リンク自体はキーワード（left_g_link / center_g_link / right_g_link）で宣言する。
「リンクしている間」は条件式 link_count、「このクリーチャーのコスト以下」は
統合後のコストを参照する式で書く。
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # 双魔左機 ミルク: 左リンク + リンク中はシールドのゴッドすべてに S・トリガーを与える
        "id": "dm23ex1-031", "name": "双魔左機 ミルク", "types": ["creature"], "civs": ["light"],
        "cost": 5, "power": 5500, "races": ["メカ・ゴッド・ノヴァOMG", "オラクル"],
        "keywords": ["s_trigger", "left_g_link"],
        "abilities": [
            {"kind": "static",
             "affects": {"zone": "shield", "owner": "you", "filter": {"race_has": "ゴッド"}},
             "if": {"cmp": [{"link_count": "self"}, ">=", 2]},
             "mod": {"grant": ["s_trigger"]}},
        ],
    },
    {   # 機械神類 ヨミ: 中央リンク + 攻撃時、コスト以下の相手を破壊し、コスト以下の味方を墓地から出す
        "id": "dm23ex1-006", "name": "機械神類 ヨミ", "types": ["creature"],
        "civs": ["light", "water", "darkness"],
        "cost": 9, "power": 15000, "races": ["メカ・ゴッド・ノヴァOMG", "オラクル"],
        "keywords": ["blocker", "powered_breaker", "center_g_link"],
        "abilities": [
            {"kind": "trigger", "when": {"event": "attack", "subject": "self"},
             "effect": [
                 {"op": "destroy",
                  "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"], "cost_le": {"cost_of": "self"}}, "count": 1}},
                 {"op": "may", "body": [
                     {"op": "move",
                      "select": {"zone": "graveyard", "owner": "you", "filter": {"types": ["creature"], "cost_le": {"cost_of": "self"}}, "count": 1},
                      "to": "bz", "reason": "put"}]},
             ]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_g_link_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
