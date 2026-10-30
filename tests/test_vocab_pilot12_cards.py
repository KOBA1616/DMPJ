"""語彙パイロット第12弾: アビスラッシュの代表カードの手変換が parse_card を通ること。

アビスラッシュはキーワード abyss_rush として置く（墓地で機能する常在型
allow: summon_from_graveyard に展開され、付随処理はエンジン側が担う）。
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # アビスラッシュ + T・ブレイカー + クリーチャーを攻撃できない
        "id": "dm22rp2x-037", "name": "ベッドウ＝ロウ", "types": ["creature"], "civs": ["darkness"],
        "cost": 5, "power": 14000, "races": ["アビスロイヤル"], "mana": 1,
        "keywords": ["abyss_rush", "triple_breaker"],
        "abilities": [
            {"kind": "static", "affects": "self", "mod": {"deny": ["attack_creature"]}},
        ],
    },
    {   # アビスラッシュ + W・ブレイカー + 出た時/離れた時、相手のパワー-4000
        "id": "dm22rp1-015", "name": "シャンデリア＝ベリア", "types": ["creature"], "civs": ["darkness"],
        "cost": 5, "power": 6000, "races": ["アビスロイヤル"], "mana": 1,
        "keywords": ["abyss_rush", "double_breaker"],
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "modify",
                         "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}, "count": 1},
                         "mod": {"power": -4000}, "duration": "end_of_turn"}]},
            {"kind": "trigger", "when": {"event": "move", "from": "bz", "subject": "self"},
             "effect": [{"op": "modify",
                         "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}, "count": 1},
                         "mod": {"power": -4000}, "duration": "end_of_turn"}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_abyss_rush_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
