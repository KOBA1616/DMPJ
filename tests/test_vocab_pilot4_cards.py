"""語彙パイロット第4弾: 鬼タイム（oni_time）の代表カードの手変換が parse_card を通ること。

鬼タイムの条件は全カード共通で「自分と相手のシールドの数が合計6つ以下」=
{cmp: [{sum: [{count: shield you}, {count: shield opp}]}, "<=", 6]}。
付与の形は常在型（static + if + mod）で、誘発に埋め込まれた形は effect 内の if で書く。
"""
import pytest

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()
ONI = {"cmp": [{"sum": [{"count": {"zone": "shield", "owner": "you"}},
                        {"count": {"zone": "shield", "owner": "opp"}}]}, "<=", 6]}

CARDS = [
    {   # ターン終わりにシールドを1つ手札へ（S・トリガーは使えない）。鬼タイムでパワー+3000
        "id": "dm24ex3-tf31", "name": "カンゴク入道", "types": ["creature"], "civs": ["fire"],
        "cost": 2, "power": 2000, "races": ["デモニオ", "鬼札王国"], "mana": 1,
        "abilities": [
            {"kind": "trigger", "when": {"event": "turn_end", "player": "you"},
             "effect": [{"op": "move", "select": {"zone": "shield", "owner": "you", "count": 1},
                         "to": "hand", "reason": "return"}]},
            {"kind": "static", "affects": "self",
             "if": ONI, "mod": {"power": 3000}},
        ],
    },
    {   # 出た時、シールドを1つ手札へ、その後、相手のアンタップしているクリーチャーを1体破壊。鬼タイムで+4000とW・ブレイカー
        "id": "dm25ex2-cho017", "name": "「大蛇」の鬼 ジャドク丸", "types": ["creature"], "civs": ["darkness"],
        "cost": 3, "power": 2000, "races": ["デモニオ", "鬼札王国"], "mana": 1,
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "move", "select": {"zone": "shield", "owner": "you", "count": 1},
                  "to": "hand", "reason": "return"},
                 {"op": "destroy",
                  "select": {"zone": "bz", "owner": "opp",
                             "filter": {"types": ["creature"], "tapped": False}, "count": 1}}]},
            {"kind": "static", "affects": "self",
             "if": ONI, "mod": {"power": 4000, "grant": ["double_breaker"]}},
        ],
    },
    {   # 攻撃する時、相手クリーチャー1体のパワーをこのターン-5000。鬼タイムで自分の全員にブロッカーとスレイヤー
        "id": "dmrp13-s09", "name": "「影斬」の鬼 ドクガン竜", "types": ["creature"],
        "civs": ["darkness", "fire"], "cost": 6, "power": 6000,
        "races": ["アーマード・ドラゴン", "鬼札王国"], "mana": 1,
        "keywords": ["speed_attacker", "double_breaker"],
        "abilities": [
            {"kind": "trigger", "when": {"event": "attack", "subject": "self"},
             "effect": [
                 {"op": "choose", "select": {"zone": "bz", "owner": "opp",
                                             "filter": {"types": ["creature"]}, "count": 1}, "as": "tgt"},
                 {"op": "modify", "select": {"ref": "tgt"}, "mod": {"power": -5000},
                  "duration": "end_of_turn"}]},
            {"kind": "static", "affects": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"]}},
             "if": ONI, "mod": {"grant": ["blocker", "slayer"]}},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_oni_time_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
