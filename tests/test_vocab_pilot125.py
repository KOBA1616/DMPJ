"""語彙パイロット第125弾: civilization_count（文明の種類数）。

「自分のマナゾーンにある文明ひとつにつき」は既存の式 civ_count で表す（新語彙なし）。
{civ_count: <selector>} は対象カード群にある文明の種類数（多色は持つ文明をすべて数える）。
mod の count、filter の式、cmp の項で使える。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()
CIVS_IN_MY_MANA = {"civ_count": {"zone": "mana", "owner": "you"}}

CARD = {
    "id": "test-cc",
    "name": "試験黙示聖霊",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 6,
    "power": 2000,
    "races": ["テスト"],
    "text": "このクリーチャーのパワーは、自分のマナゾーンにある文明ひとつにつき+4000される。",
    "abilities": [
        {"kind": "static", "affects": "self",
         "mod": {"power": {"amount": 4000, "count": CIVS_IN_MY_MANA}}},
    ],
    "source": {"official": "test-cc", "review": "pending"},
}

CARD2 = {
    "id": "test-cc2",
    "name": "試験飛忍",
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 3,
    "power": 2000,
    "races": ["テスト"],
    "text": "このクリーチャーをバトルゾーンに出した時、自分の山札を見る。その中から、自分のマナゾーンにある文明の数以下のコストを持つクリーチャーを１体選び、相手に見せてから自分の手札に加えてもよい。その後、山札をシャッフルする。",
    "abilities": [
        {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
         "effect": [
             {"op": "may", "body": [
                 {"op": "choose", "select": {"zone": "deck", "owner": "you", "look": True, "count": 1,
                                             "filter": {"types": ["creature"], "cost_le": CIVS_IN_MY_MANA}},
                  "as": "t"},
                 {"op": "move", "select": {"ref": "t", "count": "all"}, "to": "hand", "reason": "draw"},
             ]},
             {"op": "shuffle"},
         ]},
    ],
    "source": {"official": "test-cc2", "review": "pending"},
}

CARD3 = {
    "id": "test-cc3",
    "name": "試験反射光",
    "types": ["spell"],
    "civs": ["light"],
    "cost": 2,
    "text": "自分のマナゾーンにある文明の数が、相手のより多い場合、呪文を１枚、自分の墓地から手札に戻してもよい。",
    "spell": [
        {"op": "if", "cond": {"cmp": [CIVS_IN_MY_MANA, ">", {"civ_count": {"zone": "mana", "owner": "opp"}}]},
         "then": [
             {"op": "may", "body": [
                 {"op": "move", "select": {"zone": "graveyard", "owner": "you", "count": 1,
                                           "filter": {"types": ["spell"]}},
                  "to": "hand", "reason": "return"},
             ]},
         ]},
    ],
    "source": {"official": "test-cc3", "review": "pending"},
}


def test_civ_count_in_power_count_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    assert card.abilities[0]["mod"]["power"]["count"] == CIVS_IN_MY_MANA


def test_civ_count_in_filter_parses():
    card = parse_card(CARD2, TABLES)
    assert card is not None


def test_civ_count_in_cmp_parses():
    card = parse_card(CARD3, TABLES)
    assert card is not None
