"""語彙パイロット第108弾: cost_le_card（カードのコスト以下）。

選択フィルタ側の cost_le に式 {cost_of: {ref: t}} を渡すことで
「そのカードのコスト以下のカード」を表す（第82弾のイディオム）。
新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-clc2",
    "name": "試験等価探索",
    "types": ["spell"],
    "civs": ["water"],
    "cost": 4,
    "power": None,
    "races": [],
    "text": "自分の手札を1枚捨てる。そのコスト以下の進化ではないクリーチャーを1体、自分の山札から選び、相手に見せて、手札に加える。",
    "spell": [
        {"op": "select",
         "select": {"zone": "hand", "owner": "you", "count": 1},
         "as": "t",
         "then": [{"op": "move", "ref": "t", "to": "graveyard",
                   "reason": "discard"}]},
        {"op": "select",
         "select": {"zone": "deck", "owner": "you",
                    "filter": {"civs": ["water"],
                               "cost_le": {"cost_of": {"ref": "t"}}},
                    "count": 1},
         "then": [{"op": "move", "to": "hand", "reason": "put"}]},
    ],
    "source": {"official": "test-clc2", "review": "pending"},
}


def test_cost_le_ref_formula_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    step = card.spell[1]["select"]["filter"]
    assert step["cost_le"] == {"cost_of": {"ref": "t"}}


def test_cost_le_spell_shape():
    card = parse_card(CARD, TABLES)
    assert card.spell[0]["as"] == "t"
    assert card.spell[1]["select"]["zone"] == "deck"
