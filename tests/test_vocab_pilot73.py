"""語彙パイロット第73弾: zone_count_comparison（ゾーン枚数の相手比較）。

「自分の手札が相手より少ない場合」は既存の cmp + count（owner: you / opp）で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-zcc",
    "name": "試験比較獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 5,
    "power": 5000,
    "races": ["テスト"],
    "keywords": ["blocker"],
    "text": "このクリーチャーが出た時、自分の手札が相手より少ない場合、カードを１枚引いてもよい。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "summon", "subject": "self"},
         "if": {"cmp": [{"count": {"zone": "hand", "owner": "you"}}, "<",
                        {"count": {"zone": "hand", "owner": "opp"}}]},
         "effect": [
             {"op": "may", "body": [
                 {"op": "draw", "count": 1},
             ]},
         ]},
    ],
    "source": {"official": "test-zcc", "review": "pending"},
}


def test_zone_count_comparison_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = [a for a in card.abilities if a["kind"] == "trigger"][0]
    assert "cmp" in ab["if"]


def test_count_supports_opp_owner():
    # count 式が owner: opp を受理すること（parse 通過で確認済みの補強）
    card = parse_card(CARD, TABLES)
    ab = [a for a in card.abilities if a["kind"] == "trigger"][0]
    cmp_expr = ab["if"]["cmp"]
    assert cmp_expr[2]["count"]["owner"] == "opp"
