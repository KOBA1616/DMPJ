"""語彙パイロット第5弾: 代表カードの手変換が parse_card を通ること。

- entered（新規）: スピンクル（他のクリーチャーが先に出ていれば）／ハッタリ・チュリス（2体以上出なければ攻撃できない）
  ／鮮鮮-グラフィ（そのターン2体目なら）
- total_count_condition は既存: サンダイテイオー（バトルゾーン＋マナゾーンの種族カード合計は sum of counts、
  G・ゼロは free_if でも同じ条件が使える）
"""
import pytest

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()
SECOND = {"all": [{"cmp": [{"entered": {"owner": "you"}}, ">=", 2]},
                  {"cmp": [{"entered": {"owner": "you"}}, "<", 3]}]}   # 「２体目」: cmp に = は無いので挟む

CARDS = [
    {   # 出た時、すでに自分の他のクリーチャーが出ていれば、このターンSAを得る
        "id": "dmrp11-054", "name": "スリップ尖車 スピンクル", "types": ["creature"], "civs": ["fire"],
        "cost": 2, "power": 2000, "races": ["ビートジョッキー"], "mana": 1,
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "if", "cond": {"cmp": [{"entered": {"owner": "you", "other": True}}, ">=", 1]},
                         "then": [{"op": "modify", "select": {"ref": "self"},
                                   "mod": {"grant": ["speed_attacker"]}, "duration": "end_of_turn"}]}]},
        ],
    },
    {   # このターン2体以上出ていなければ攻撃できない
        "id": "dmrp11-095", "name": "ハッタリ・チュリス", "types": ["creature"], "civs": ["fire"],
        "cost": 2, "power": 5000, "races": ["ビートジョッキー"], "mana": 1,
        "abilities": [
            {"kind": "static", "affects": "self",
             "if": {"cmp": [{"entered": {"owner": "you"}}, "<", 2]},
             "mod": {"deny": ["attack_player", "attack_creature"]}},
        ],
    },
    {   # 自分のクリーチャーが出た時、それが2体目なら、相手1体をタップして凍結する
        "id": "dmrp13-031", "name": "鮮鮮-グラフィ", "types": ["creature"], "civs": ["light"],
        "cost": 3, "power": 3500, "races": ["バーサーカー", "チームボンバー"], "mana": 1,
        "abilities": [
            {"kind": "trigger",
             "when": {"event": "move", "to": "bz", "subject": {"owner": "you", "filter": {"types": ["creature"]}}},
             "if": SECOND,
             "effect": [
                 {"op": "choose", "select": {"zone": "bz", "owner": "opp",
                                             "filter": {"types": ["creature"]}, "count": 1}, "as": "tgt"},
                 {"op": "tap", "select": {"ref": "tgt"}, "no_untap_next": True}]},
        ],
    },
    {   # 自分のジョーカーズ（場＋マナ）が合計7つ以上なら、シールドゾーンでS・トリガーを得る
        "id": "dm26rp3-s006", "name": "闘帝合体 サンダイテイオー", "types": ["creature"], "civs": ["nature"],
        "cost": 8, "power": 13000, "races": ["ジョーカーズ"], "mana": 1,
        "keywords": ["triple_breaker"],
        "abilities": [
            # マッハファイター（keyword_patterns の展開形）
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "modify", "select": {"ref": "self"},
                         "mod": {"allow": [{"action": "attack_creature", "other": {"tapped": False}}]},
                         "duration": "end_of_turn"}]},
            {"kind": "static", "affects": "self", "zone": "shield",
             "if": {"cmp": [{"sum": [{"count": {"zone": "bz", "owner": "you", "filter": {"race_has": "ジョーカーズ"}}},
                                     {"count": {"zone": "mana", "owner": "you", "filter": {"race_has": "ジョーカーズ"}}}]},
                            ">=", 7]},
             "mod": {"grant": ["s_trigger"]}},
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "modal", "count": 3, "modes": [
                     [{"op": "choose", "select": {"zone": "bz", "owner": "opp",
                                                  "filter": {"types": ["creature"]}, "count": 1}, "as": "tgt"},
                      {"op": "move", "select": {"ref": "tgt"}, "to": "mana", "reason": "put"}],
                     [{"op": "move", "select": {"zone": "deck", "owner": "you", "from_top": 1},
                       "to": "mana", "reason": "charge"}],
                     [{"op": "choose", "select": {"zone": "mana", "owner": "you",
                                                  "filter": {"types": ["creature"]}, "count": 1}, "as": "back"},
                      {"op": "move", "select": {"ref": "back"}, "to": "hand", "reason": "return"}],
                 ]}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_representative_reject_now_parses5(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
