"""語彙パイロット第127弾: indestructible（破壊されない）。

「このクリーチャーは破壊されない」は static の mod: {indestructible: true} で表す（新語彙）。
エンジン: chars に indestructible を集め、events._apply_one が置換後の最終的な
破壊（reason: destroy で墓地へ）を防ぐ。バトルでも battle_indestructible と同様に扱う。
条件つきは static の if、付与は modify の mod で同じ形を使う。
"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-ind",
    "name": "試験不壊獣",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "このクリーチャーは破壊されない。",
    "abilities": [
        {"kind": "static", "affects": "self", "mod": {"indestructible": True}},
    ],
    "source": {"official": "test-ind", "review": "pending"},
}


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def keys(d):
    return [o["key"] for o in d["options"]]


def test_indestructible_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    assert card.abilities[0]["mod"]["indestructible"] is True


def test_indestructible_invalid():
    bad = dict(CARD, id="test-ind-bad")
    bad["abilities"] = [{"kind": "static", "affects": "self", "mod": {"indestructible": "yes"}}]
    try:
        parse_card(bad, TABLES)
        assert False, "should have raised"
    except Exception as e:
        assert "indestructible" in str(e)


def to_attack(e):
    d = e.advance()
    while d["kind"] in ("charge", "main"):
        e.answer([keys(d).index("pass")])
        d = e.advance()
    assert d["kind"] == "attack", d["kind"]
    return d


def finish(e, d):
    while d is not None and d["kind"] not in ("charge", "main"):
        if d["kind"] == "block":
            e.answer([keys(d).index("no_block")])
        else:
            e.answer([0])
        d = e.advance()


def test_indestructible_survives_battle(rr):
    """タップした R090（3000）が R070（4000）に攻撃される: バトルで負けても破壊されない。"""
    e = setup(rr, {"bz": ["R070"]}, {"bz": ["R090"]})
    e.s.cards[e.bz_tops(1)[0]].tapped = True
    d = to_attack(e)
    e.answer([keys(d).index("attack:R070:R090")])
    finish(e, e.advance())
    assert [c.defn for c in e.s.cards if c.zone == "bz" and c.owner == 1] == ["R090"]


def test_indestructible_survives_destroy_effect(rr):
    """R082 の攻撃時破壊（パワー小さい相手を破壊）が R090 に向く: 破壊されない。"""
    e = setup(rr, {"bz": ["R082"]}, {"bz": ["R090"]})
    d = to_attack(e)
    e.answer([keys(d).index("attack:R082:player")])
    finish(e, e.advance())
    assert [c.defn for c in e.s.cards if c.zone == "bz" and c.owner == 1] == ["R090"]


def test_plain_creature_destroyed_by_effect(rr):
    """対照: R076（2000）は R082 の破壊で墓地に置かれる。"""
    e = setup(rr, {"bz": ["R082"]}, {"bz": ["R076"]})
    d = to_attack(e)
    e.answer([keys(d).index("attack:R082:player")])
    finish(e, e.advance())
    assert e.bz_tops(1) == []
