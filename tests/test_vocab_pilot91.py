"""語彙パイロット第91弾: next_summon_cost_reduction（次に召喚するコスト軽減）。

「このターン、次に召喚する自分の〜のコストをN少なくする」は cost_may（once）の modify で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-nsc",
    "name": "試験軽減呪文",
    "types": ["spell"],
    "civs": ["zero"],
    "cost": 2,
    "text": "このターン、次に召喚する自分の無色クリーチャーの召喚コストを最大５少なくする。",
    "spell": [
        {"op": "may",
         "body": [
             {"op": "modify",
              "select": {"zone": "hand", "owner": "you",
                         "filter": {"types": ["creature"], "colorless": True}},
              "mod": {"cost_may": {"amount": 5, "min": 0, "once": True}},
              "duration": "end_of_turn",
              "dynamic": True},
         ]},
    ],
    "source": {"official": "test-nsc", "review": "pending"},
}


def test_next_summon_cost_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    step = card.spell[0]
    assert step["op"] == "may"


def test_next_summon_cost_mod():
    card = parse_card(CARD, TABLES)
    mod = card.spell[0]["body"][0]["mod"]["cost_may"]
    assert mod["amount"] == 5
    assert mod["once"] is True
