"""語彙パイロット第64弾: must_attack_this_creature（相手は可能ならこのクリーチャーを攻撃する）。

「相手は可能ならこのクリーチャーを攻撃する」は既存の mod: {must_be_attacked: true} で表す。
新語彙なし。第51弾で実装済み。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-mac",
    "name": "試験誘攻獣",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 4,
    "power": 4000,
    "races": ["テスト"],
    "keywords": ["enters_tapped"],
    "text": "相手は可能ならこのクリーチャーを攻撃する。",
    "abilities": [
        {"kind": "static", "affects": "self",
         "mod": {"must_be_attacked": True}},
    ],
    "source": {"official": "test-mac", "review": "pending"},
}


def test_must_attack_this_creature_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    assert ab["mod"]["must_be_attacked"] is True


def test_must_attack_this_creature_invalid():
    bad = {
        "id": "test-mac-bad",
        "name": "試験誘攻獣不良",
        "types": ["creature"],
        "civs": ["light"],
        "cost": 4,
        "power": 4000,
        "abilities": [
            {"kind": "static", "affects": "self",
             "mod": {"must_be_attacked": "yes"}},
        ],
        "source": {"official": "test-mac-bad", "review": "pending"},
    }
    try:
        parse_card(bad, TABLES)
        assert False, "should have raised"
    except Exception as e:
        assert "must_be_attacked" in str(e)
