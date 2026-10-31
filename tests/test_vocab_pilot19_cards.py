"""語彙パイロット第19弾: ハイパーモードの代表カードの手変換が parse_card を通ること。

変換の型: 面に hyper: true を置き、ハイパーモードでだけ働く能力に条件 {hyper: true} を付ける。
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # ハッター・ルピア: ハイパーモード中、相手のマナ枚数よりコストが大きい相手クリーチャーが出たら破壊する
        "id": "dm24ex1-019", "name": "ハッター・ルピア", "types": ["creature"], "civs": ["nature"],
        "cost": 3, "power": 2000, "races": ["ミルク・ボーイ", "ハンター"],
        "hyper": True,
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": {"owner": "opp"}},
             "if": {"hyper": True},
             "effect": [
                 {"op": "if", "cond": {"cmp": [{"cost_of": {"ref": "subject"}}, ">", {"count": {"zone": "mana", "owner": "opp"}}]},
                  "then": [{"op": "destroy", "select": {"ref": "subject"}}]}]},
        ],
    },
    {   # 料理犬のヴィヤンドゥ: マッハファイター + ハイパー化のみ（能力はキーワード展開形）
        "id": "dm24ex1-022", "name": "料理犬のヴィヤンドゥ", "types": ["creature"], "civs": ["fire"],
        "cost": 2, "power": 2000, "races": ["アーマード・ワイバーン", "ハンター"],
        "hyper": True,
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "modify", "select": {"ref": "self"},
                  "mod": {"allow": [{"action": "attack_creature", "other": {"tapped": False}}]},
                  "duration": "end_of_turn"}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_hyper_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
