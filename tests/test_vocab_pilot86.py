"""語彙パイロット第86弾: thrilling_three（スリリング・スリー）。

「上から3枚を表向きにし、該当1体につき能力を1回、その後すべて山札の下へ」は
choose(look) + repeat(times=count式) + move で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-tt",
    "name": "試験スリー獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 5,
    "power": 4000,
    "races": ["グレートメカオー"],
    "text": "このクリーチャーをバトルゾーンに出した時、自分の山札の上から３枚を表向きにする。表向きにしたグレートメカオー１体につき、カードを１枚引いてもよい。その後、表向きにしたカードをすべて、好きな順序で山札の一番下に戻す。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "summon", "subject": "self"},
         "effect": [
             {"op": "choose",
              "select": {"zone": "deck", "owner": "you", "from_top": 3, "look": True},
              "as": "pile"},
             {"op": "repeat",
              "times": {"count": {"ref": "pile", "filter": {"race_has": "グレートメカオー"}}},
              "body": [
                  {"op": "may", "body": [{"op": "draw", "count": 1}]},
              ]},
             {"op": "move",
              "select": {"ref": "pile"},
              "to": "deck", "reason": "put", "position": "bottom", "order": "choose"},
         ]},
    ],
    "source": {"official": "test-tt", "review": "pending"},
}


def test_thrilling_three_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    rep = ab["effect"][1]
    assert rep["op"] == "repeat"
    assert rep["times"]["count"]["ref"] == "pile"


def test_thrilling_three_return():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    mv = ab["effect"][2]
    assert mv["to"] == "deck" and mv["position"] == "bottom"
