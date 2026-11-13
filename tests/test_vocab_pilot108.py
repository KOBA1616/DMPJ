"""語彙パイロット第108弾: cost_le_card（カードのコスト以下）。

選択フィルタ側の cost_le に式 {cost_of: {ref: t}} を渡すことで
「そのカードのコスト以下のカード」を表す（第82弾のイディオム）。
選択は op に select を埋め込む形（move + select + as で束縛）。
新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-clc2",
    "name": "試験等価探索",
    "types": ["spell"],
    "civs": ["water"],
    "cost": 4,
    "power": None,
    "races": [],
    "text": "自分の手札を1枚捨てる。そのコスト以下のクリーチャーを1体、自分の山札から選び、手札に加える。",
    "spell": [
        {"op": "move",
         "select": {"zone": "hand", "owner": "you", "count": 1},
         "as": "t",
         "to": "graveyard", "reason": "discard"},
        {"op": "move",
         "select": {"zone": "deck", "owner": "you",
                    "filter": {"civs": ["water"],
                               "cost_le": {"cost_of": {"ref": "t"}}},
                    "count": 1},
         "to": "hand", "reason": "put"},
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
