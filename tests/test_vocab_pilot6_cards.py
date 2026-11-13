"""語彙パイロット第6弾: summon_time_cost の代表カードの手変換が parse_card を通ること。

いずれも「召喚する時、〜してもよい。そうしたら/につき、コストをN少なくする」を
常在型（手札で効く）mod の opt_reduce {do: ...} で書く。
"""
import pytest

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # 手札から進化クリーチャーを1体見せると-2（下限0）。自分のターンの終わりにアンタップする
        "id": "dmr18-027", "name": "侵略者 ノイバウテン", "types": ["creature"], "civs": ["light"],
        "cost": 5, "power": 4000, "races": ["エンジェル・コマンド", "侵略者"], "mana": 1,
        "abilities": [
            {"kind": "static", "affects": "self", "zone": "hand",
             "mod": {"opt_reduce": {"amount": 2, "floor": 0,
                                    "do": {"select": {"zone": "hand", "owner": "you",
                                                      "filter": {"types": ["evolution"]}, "other": True},
                                           "min": 1, "max": 1}}}},
            {"kind": "trigger", "when": {"event": "turn_end", "player": "you"},
             "effect": [{"op": "untap", "select": {"ref": "self"}}]},
        ],
    },
    {   # 手札を1枚捨てると-3
        "id": "dmrp13-037", "name": "ダースシギ卿", "types": ["creature"], "civs": ["darkness"],
        "cost": 5, "power": 5000, "races": ["ファンキー・ナイトメア", "不死樹王国"], "mana": 1,
        "abilities": [
            {"kind": "static", "affects": "self", "zone": "hand",
             "mod": {"opt_reduce": {"amount": 3, "floor": 0,
                                    "do": {"select": {"zone": "hand", "owner": "you", "other": True},
                                           "min": 1, "max": 1, "move_to": "graveyard"}}}},
        ],
    },
    {   # 墓地の呪文を好きな数山札に戻し、1枚につき-1（下限1）。自分の水の呪文を唱えた時、カード1枚を手札に戻してもよい
        "id": "dmr15-002", "name": "龍素記号Mj リンシャンカイホ", "types": ["creature"], "civs": ["water"],
        "cost": 12, "power": 12000, "races": ["クリスタル・コマンド・ドラゴン"], "mana": 1,
        "keywords": ["triple_breaker"],
        "abilities": [
            {"kind": "static", "affects": "self", "zone": "hand",
             "mod": {"opt_reduce": {"amount": 1, "per": True, "floor": 1,
                                    "do": {"select": {"zone": "graveyard", "owner": "you",
                                                      "filter": {"types": ["spell"]}},
                                           "min": 0, "max": 99, "move_to": "deck", "shuffle": True}}}},
            {"kind": "trigger",
             "when": {"event": "cast", "player": "you",
                      "subject": {"owner": "you", "filter": {"types": ["spell"], "civs": ["water"]}}},
             "effect": [{"op": "may", "body": [
                 {"op": "choose", "select": {"zone": "bz", "owner": "any", "count": 1}, "as": "tgt"},
                 {"op": "move", "select": {"ref": "tgt"}, "to": "hand", "reason": "return"}]}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_summon_time_cost_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
