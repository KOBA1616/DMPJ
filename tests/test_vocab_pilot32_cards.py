"""語彙パイロット第32弾: 代表カードの手変換が parse_card を通ること。

- ネオ・スレッジハンマー: when の attacker: crossed（これをクロスしたクリーチャーがブロックされた時）
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # ネオ・スレッジハンマー: クロス先への常在型＋ブロック時誘発（attacker: crossed）
        "id": "dm14-070", "name": "ネオ・スレッジハンマー", "types": ["cross_gear"], "civs": ["fire"],
        "cost": 3,
        "abilities": [
            {"kind": "static", "affects": "crossed", "mod": {"power_when": {"amount": 3000, "when": "attacking"}}},
            {"kind": "trigger", "when": {"event": "block", "attacker": "crossed"},
             "effect": [{"op": "break", "player": "opp", "count": 1}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_phase10_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
