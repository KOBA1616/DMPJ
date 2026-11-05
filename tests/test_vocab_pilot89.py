"""語彙パイロット第89弾: does_not_untap_next_turn（次のターンのはじめにアンタップしない）。

「タップし、次のターンのはじめにアンタップしない」は tap の no_untap_next: true で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-dnt",
    "name": "試験凍結獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "このクリーチャーが出た時、相手のクリーチャーを１体選んでタップする。次の相手のターンのはじめに、そのクリーチャーはアンタップしない。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "summon", "subject": "self"},
         "effect": [
             {"op": "tap",
              "select": {"zone": "bz", "owner": "opp", "count": 1,
                         "filter": {"types": ["creature"]}},
              "no_untap_next": True},
         ]},
    ],
    "source": {"official": "test-dnt", "review": "pending"},
}


def test_no_untap_next_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["effect"][0]["no_untap_next"] is True


def test_no_untap_next_op():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["effect"][0]["op"] == "tap"
