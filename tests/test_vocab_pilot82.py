"""語彙パイロット第82弾: cost_le_card_cost（そのカード以下のコスト）。

filter の cost_le は式を受け付ける（FILTER_EXPR_KEYS）。{cost_of: {ref: ...}} で
束縛したカードのコスト以下を表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-clc",
    "name": "試験以下獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "このクリーチャーが出た時、相手は自身の山札の上から１枚目を墓地に置く。そのカード以下のコストを持つ相手のエレメントを１つ選び、持ち主の手札に戻す。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "summon", "subject": "self"},
         "effect": [
             {"op": "move",
              "select": {"zone": "deck", "owner": "opp", "from_top": 1},
              "as": "milled",
              "to": "graveyard", "reason": "put"},
             {"op": "bounce",
              "select": {"zone": "bz", "owner": "opp", "count": 1,
                         "filter": {"cost_le": {"cost_of": {"ref": "milled"}}}}},
         ]},
    ],
    "source": {"official": "test-clc", "review": "pending"},
}


def test_cost_le_card_cost_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    f = ab["effect"][1]["select"]["filter"]
    assert f["cost_le"] == {"cost_of": {"ref": "milled"}}


def test_cost_ge_expr_parses():
    card2 = {
        "id": "test-clc2",
        "name": "試験以上獣",
        "types": ["creature"],
        "civs": ["fire"],
        "cost": 5,
        "power": 5000,
        "races": ["テスト"],
        "text": "このクリーチャーが出た時、自分の山札の上から１枚目を見る。それ以上のコストを持つクリーチャーを１体破壊する。",
        "abilities": [
            {"kind": "trigger",
             "when": {"event": "summon", "subject": "self"},
             "effect": [
                 {"op": "choose",
                  "select": {"zone": "deck", "owner": "you", "from_top": 1,
                             "look": True},
                  "as": "t"},
                 {"op": "destroy",
                  "select": {"zone": "bz", "owner": "any", "count": 1,
                             "filter": {"types": ["creature"],
                                        "cost_ge": {"cost_of": {"ref": "t"}}}}},
             ]},
        ],
        "source": {"official": "test-clc2", "review": "pending"},
    }
    parsed = parse_card(card2, TABLES)
    assert parsed is not None
