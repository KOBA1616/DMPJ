"""語彙パイロット第133弾: cost_lt_card_cost（参照カードよりコストが小さい）。

「その捨てたカードよりコストが小さい相手のクリーチャーを破壊する」は
filter: {cost_le: {sum: [{cost_of: {ref: X}}, -1]}} で表す。新語彙なし（第82・85弾の応用）。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-clcc",
    "name": "試験捨札獣",
    "types": ["creature"],
    "civs": ["darkness"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "自分のターンの終わりに、クリーチャーを１体、自分の手札から捨ててもよい。そうした場合、そのクリーチャーよりコストが小さい相手のクリーチャーを１体破壊する。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "turn_end", "subject": "self"},
         "if": {"is_turn": "you"},
         "effect": [
             {"op": "may", "body": [
                 {"op": "discard",
                  "select": {"zone": "hand", "owner": "you", "count": 1,
                             "filter": {"types": ["creature"]}},
                  "as": "dropped"},
                 {"op": "destroy",
                  "select": {"zone": "bz", "owner": "opp", "count": 1,
                             "filter": {"types": ["creature"],
                                        "cost_le": {"sum": [{"cost_of": {"ref": "dropped"}}, -1]}}}},
             ]},
         ]},
    ],
    "source": {"official": "test-clcc", "review": "pending"},
}


def test_cost_lt_card_cost_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"


def test_cost_lt_card_cost_filter():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    destroy = ab["effect"][0]["body"][1]
    assert destroy["reason"] == "destroy"   # destroy は move（reason: destroy）に正規化される
    assert "cost_le" in destroy["select"]["filter"]
