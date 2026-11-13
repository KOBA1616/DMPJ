"""語彙パイロット第121弾: total_count_condition（合計数条件）。

「自分の、ジョーカーズとマナゾーンにあるジョーカーズ・カードが合計７つ以上なら」は
count セレクタ（フィルタ付き）の sum を cmp で比較して表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

TOTAL7 = {"sum": [
    {"count": {"zone": "bz", "owner": "you", "filter": {"races": ["ジョーカーズ"]}}},
    {"count": {"zone": "mana", "owner": "you", "filter": {"races": ["ジョーカーズ"]}}},
]}

CARD = {
    "id": "test-tcc",
    "name": "試験合算獣",
    "types": ["creature"],
    "civs": ["zero"],
    "cost": 7,
    "power": 7000,
    "races": ["ジョーカーズ"],
    "text": "自分の、ジョーカーズとマナゾーンにあるジョーカーズ・カードが合計７つ以上なら、このクリーチャーは「スピードアタッカー」を得る。",
    "abilities": [
        {"kind": "static",
         "affects": "self",
         "if": {"cmp": [TOTAL7, ">=", 7]},
         "mod": {"grant": ["speed_attacker"]}},
    ],
    "source": {"official": "test-tcc", "review": "pending"},
}


def test_total_count_static_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    assert ab["if"]["cmp"][1] == ">="


def test_total_count_expr_shape():
    card = parse_card(CARD, TABLES)
    expr = card.abilities[0]["if"]["cmp"][0]
    assert expr["sum"][0]["count"]["zone"] == "bz"
    assert expr["sum"][1]["count"]["zone"] == "mana"
