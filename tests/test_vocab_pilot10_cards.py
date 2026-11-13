"""語彙パイロット第10弾: スペース・チャージの代表カードの手変換が parse_card を通ること。

変換の型: 文明ごとの行を optional な誘発に分け、when の subject フィルタで
「自分のマナゾーンに置かれた、その文明のカード」を指定する。
"""
import pytest

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()


def sc(civs, effect):
    # 「使ってもよい」は効果側の may で表す（誘発の optional はエンジンでは効かない）
    return {"kind": "trigger", "optional": True,
            "when": {"event": "move", "to": "mana", "subject": {"owner": "you", "filter": {"civs": civs}}},
            "effect": [{"op": "may", "body": effect}]}


CARDS = [
    {   # 出た時タップ＋次の自分のターンのはじめまでアンタップしない。SC闇: このターン パワー-2000
        "id": "dm26rp2-029", "name": "鎧亜寄生パラス・キューピッド", "types": ["creature"], "civs": ["light"],
        "cost": 3, "power": 4000, "races": ["ロスト・クルセイダー", "エイリアン"], "mana": 1,
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "tap", "select": {"zone": "bz", "owner": "opp",
                                                 "filter": {"types": ["creature"]}, "count": 1},
                         "no_untap_next": True}]},
            sc(["darkness"], [{"op": "modify",
                               "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}, "count": 1},
                               "mod": {"power": -2000}, "duration": "end_of_turn"}]),
        ],
    },
    {   # 出た時、山札の上から2枚をタップしてマナへ。SC 4行（マッハファイターは展開形）
        "id": "dm26rp2-010", "name": "鎧亜目邪王類 デス＝ヴェルムート", "types": ["creature"], "civs": ["nature"],
        "cost": 5, "power": 6000, "races": ["ジュラシック・コマンド・ドラゴン", "革命軍", "ハムカツ団"], "mana": 1,
        "keywords": ["powered_breaker"],
        "abilities": [
            {"kind": "static", "affects": "self",
             "mod": {"allow": [{"action": "attack_creature", "other": {"tapped": False}}]}},
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "move", "select": {"zone": "deck", "owner": "you", "from_top": 2},
                         "to": "mana", "reason": "charge", "tapped": True}]},
            sc(["light"], [{"op": "move", "select": {"zone": "deck", "owner": "you", "from_top": 1},
                            "to": "shield", "reason": "put"}]),
            sc(["water"], [{"op": "bounce", "select": {"zone": "bz", "owner": "opp",
                                                       "filter": {"types": ["creature"]}, "count": 1}}]),
            sc(["darkness"], [{"op": "discard", "select": {"zone": "hand", "owner": "opp",
                                                           "chooser": "opp", "count": 1}}]),
            sc(["fire"], [{"op": "modify",
                           "select": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"]}, "count": 1},
                           "mod": {"power": 6000}, "duration": "end_of_turn"}]),
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_space_charge_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
