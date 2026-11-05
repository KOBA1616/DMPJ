"""語彙パイロット第70弾: ability_ignore（能力を無視する）。

「〜の能力を無視する」は既存の mod: {ignore: [all]} で表す（modify で付与）。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-ai",
    "name": "試験無視獣",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 6,
    "power": 6000,
    "races": ["テスト"],
    "text": "このクリーチャーが出た時、次の自分のターンのはじめまで、相手のクリーチャーすべての能力を無視する。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "summon", "subject": "self"},
         "effect": [
             {"op": "modify",
              "select": {"zone": "bz", "owner": "opp",
                         "filter": {"types": ["creature"]}, "count": "all"},
              "mod": {"ignore": ["all"]},
              "duration": "until_next_own_turn_start"},
         ]},
    ],
    "source": {"official": "test-ai", "review": "pending"},
}


def test_ability_ignore_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"
    assert ab["effect"][0]["mod"]["ignore"] == ["all"]


def test_ability_ignore_mod_key():
    from dmsim.defs import MOD_KEYS
    assert "ignore" in MOD_KEYS
