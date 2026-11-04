"""語彙パイロット第9弾: optional_cost_reduction（常在型）の代表カードの手変換が parse_card を通ること。

「自分の〜のコストをN少なくしてもよい」は、発生源の常在型に
mod {cost_may: {amount, once?, min}} を持たせ、affects で対象（手札のカード）を指定する。
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # 各ターンに1度、自分の光/水/自然のクリーチャーの召喚コストを1少なくしてもよい
        "id": "dm25ex3-063", "name": "奇跡妖精ヴェヌス", "types": ["creature"], "civs": ["light"],
        "cost": 2, "power": 3000, "races": ["スノーフェアリー"], "mana": 1, "keywords": ["g_strike"],
        "abilities": [
            {"kind": "static",
             "affects": {"zone": "hand", "owner": "you",
                         "filter": {"types": ["creature"], "civs": ["light", "water", "nature"]}},
             "mod": {"cost_may": {"amount": 1, "once": True, "min": 0}}},
        ],
    },
    {   # 自分の呪文を唱えるコストを1少なくしてもよい（ターン1回制限なし）
        "id": "dmpcd02-b13", "name": "氷牙フランツI世", "types": ["creature"], "civs": ["water"],
        "cost": 3, "power": 2000, "races": ["サイバーロード", "ナイト"], "mana": 1,
        "abilities": [
            {"kind": "static",
             "affects": {"zone": "hand", "owner": "you", "filter": {"types": ["spell"]}},
             "mod": {"cost_may": {"amount": 1, "min": 0}}},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_cost_may_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
