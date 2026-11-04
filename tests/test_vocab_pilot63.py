"""語彙パイロット第63弾: force_attack（可能なら攻撃する）。

「可能であれば攻撃する」は既存の require: ["attack"] で表す。
新語彙なし。エンジン（turn.py）が強制攻撃を処理済み。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-fa",
    "name": "試験強攻獣",
    "types": ["creature"],
    "civs": ["darkness"],
    "cost": 4,
    "power": 4000,
    "races": ["テスト"],
    "text": "次の相手のターン中、そのクリーチャーは可能であれば攻撃する。",
    "abilities": [
        {"kind": "static",
         "affects": {"zone": "bz", "owner": "opp",
                     "filter": {"types": ["creature"]}},
         "mod": {"require": ["attack"]}},
    ],
    "source": {"official": "test-fa", "review": "pending"},
}


def test_force_attack_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    assert ab["mod"]["require"] == ["attack"]


def test_force_attack_invalid():
    bad = {
        "id": "test-fa-bad",
        "name": "試験強攻獣不良",
        "types": ["creature"],
        "civs": ["darkness"],
        "cost": 4,
        "power": 4000,
        "abilities": [
            {"kind": "static", "affects": "self",
             "mod": {"require": ["invalid_action"]}},
        ],
        "source": {"official": "test-fa-bad", "review": "pending"},
    }
    try:
        parse_card(bad, TABLES)
        assert False, "should have raised"
    except Exception as e:
        assert "require" in str(e)
