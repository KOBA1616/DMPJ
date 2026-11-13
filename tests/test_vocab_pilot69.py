"""語彙パイロット第69弾: kourin（光臨）。

「光臨：自分のターンの終わりに、このクリーチャーがタップされていれば、〜」は
既存の trigger + if: {exists: {ref: self, filter: {tapped: true}}} で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-kr",
    "name": "試験光臨獣",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 5,
    "power": 5000,
    "races": ["テスト"],
    "text": "光臨：自分のターンの終わりに、このクリーチャーがタップされていれば、自分の山札を見る。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "turn_end", "player": "you"},
         "if": {"exists": {"ref": "self", "filter": {"tapped": True}}},
         "effect": [
             {"op": "draw", "count": 1},
         ]},
    ],
    "source": {"official": "test-kr", "review": "pending"},
}


def test_kourin_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"
    assert "exists" in ab["if"]


def test_kourin_tapped_condition():
    # tapped フィルタが有効であることを確認
    from dmsim.cards.defs import FILTER_KEYS
    assert "tapped" in FILTER_KEYS
