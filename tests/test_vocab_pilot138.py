"""語彙パイロット第138弾: filter_or_race_or_type（種族またはタイプの選択）。

「ゴッドまたは呪文を１枚選ぶ」は filter: {any_of: [{race_has: ゴッド}, {types: [spell]}]}。
新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-fot",
    "name": "試験探求呪文",
    "types": ["spell"],
    "civs": ["water"],
    "cost": 3,
    "races": ["テスト"],
    "text": "自分の山札の上から３枚を見る。その中からゴッドまたは呪文を１枚選んで相手に見せ、手札に加える。残りを好きな順序で山札の下に置く。",
    "spell": [
        {"op": "move",
         "select": {"zone": "deck", "owner": "you", "from_top": 3, "count": 1, "look": True,
                    "filter": {"any_of": [{"race_has": "ゴッド"}, {"types": ["spell"]}]}},
         "to": "hand", "reason": "draw"},
    ],
    "source": {"official": "test-fot", "review": "pending"},
}


def test_or_filter_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    assert len(card.spell) == 1


def test_or_filter_shape():
    card = parse_card(CARD, TABLES)
    f = card.spell[0]["select"]["filter"]
    assert f["any_of"][0] == {"race_has": "ゴッド"}
    assert f["any_of"][1] == {"types": ["spell"]}
