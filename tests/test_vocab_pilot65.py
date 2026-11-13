"""語彙パイロット第65弾: cost_gt_count（コストがゾーンの枚数より大きい）。

「相手のマナゾーンにあるカードの枚数よりコストが大きい」は
既存の if: {cmp: [{cost_of: ...}, ">", {count: ...}]} で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-cgc",
    "name": "試験数超獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 5,
    "power": 5000,
    "races": ["テスト"],
    "text": "相手のクリーチャーが出た時、それが相手のマナゾーンにあるカードの枚数よりコストが大きいクリーチャーなら、持ち主の手札に戻してもよい。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "summon", "subject": {"owner": "opp"}},
         "if": {"cmp": [{"cost_of": {"ref": "event.subject"}}, ">",
                        {"count": {"zone": "mana", "owner": "opp"}}]},
         "effect": [
             {"op": "may", "body": [
                 {"op": "move", "select": {"ref": "event.subject"},
                  "to": "hand", "reason": "return"},
             ]},
         ]},
    ],
    "source": {"official": "test-cgc", "review": "pending"},
}


def test_cost_gt_count_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"
    assert "cmp" in ab["if"]


def test_cost_gt_count_invalid():
    bad = {
        "id": "test-cgc-bad",
        "name": "試験数超獣不良",
        "types": ["creature"],
        "civs": ["water"],
        "cost": 5,
        "power": 5000,
        "abilities": [
            {"kind": "trigger",
             "when": {"event": "summon", "subject": {"owner": "opp"}},
             "if": {"cmp": [{"cost_of": {"ref": "event.subject"}}, "!=",
                            {"count": {"zone": "mana", "owner": "opp"}}]},
             "effect": [{"op": "may", "body": []}]},
        ],
        "source": {"official": "test-cgc-bad", "review": "pending"},
    }
    try:
        parse_card(bad, TABLES)
        assert False, "should have raised"
    except Exception as e:
        assert "cmp" in str(e)
