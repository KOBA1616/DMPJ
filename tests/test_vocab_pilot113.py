"""語彙パイロット第113弾: draw_replacement（引くかわりに）。

「自分がカードを引く時、1枚のかわりに2枚引いてもよい。そうした場合、
自分の手札を1枚捨てる」は draw イベントへの置換（replace + instead）で表す。
新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-dr",
    "name": "試験倍引獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "自分がカードを引く時、１枚のかわりに２枚引いてもよい。そうした場合、自分の手札を１枚捨てる。",
    "abilities": [
        {"kind": "replace",
         "when": {"event": "draw", "player": "you"},
         "optional": True,
         "instead": [
             {"op": "draw", "count": 2},
             {"op": "discard",
              "select": {"zone": "hand", "owner": "you", "count": 1}},
         ]},
    ],
    "source": {"official": "test-dr", "review": "pending"},
}


def test_draw_replace_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "replace"
    assert ab["optional"] is True


def test_draw_replace_instead_shape():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["when"]["event"] == "draw"
    assert ab["instead"][0] == {"op": "draw", "count": 2}
