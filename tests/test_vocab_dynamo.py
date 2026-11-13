"""語彙拡張: ダイナモ（攻撃できる時、またはバトルが始まる時にタップしてもよい。そうした場合、そのターンの終わりまで、
このクリーチャーのパワーと能力を自分の他のダイナモ1体に加える）。602.3a 攻撃できる時だけ起動できる。701.13 バトル。"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def keys(d):
    return [o["key"] for o in d["options"]]


def to_attack(e):
    d = e.advance()
    while d["kind"] in ("charge", "main"):
        e.answer([keys(d).index("pass")])
        d = e.advance()
    assert d["kind"] == "attack", d["kind"]
    return d


def by(e, defn):
    return next(c for c in e.bz_tops(0) if e.s.cards[c].defn == defn)


def test_activate_adds_power_and_abilities(rr):
    """攻撃できる時、タップして使うと、他のダイナモにパワーとブロッカーが加わる。ダイナモ自身の能力は加わらない。"""
    e = setup(rr, {"bz": ["R068", "R069"]})
    d = to_attack(e)
    k = next(x for x in keys(d) if x.startswith("activate:R068"))
    assert e.chars(by(e, "R069"))["power"] == 2000 and "blocker" not in e.chars(by(e, "R069"))["keywords"]
    e.answer([keys(d).index(k)])
    e.advance()
    w = by(e, "R069")
    assert e.s.cards[by(e, "R068")].tapped
    assert e.chars(w)["power"] == 5000 and "blocker" in e.chars(w)["keywords"]
    assert [ab["keyword"] for _, ab in e.abilities(w, "activate")] == ["dynamo"]     # 自分のダイナモだけ。加えられた分はない


def test_activate_needs_another_dynamo(rr):
    """加える先の他のダイナモがいなければ起動できない。"""
    e = setup(rr, {"bz": ["R068"]})
    d = to_attack(e)
    assert not [x for x in keys(d) if x.startswith("activate")]


def test_effect_ends_at_end_of_turn(rr):
    e = setup(rr, {"bz": ["R068", "R069"]})
    d = to_attack(e)
    e.answer([keys(d).index(next(x for x in keys(d) if x.startswith("activate:R068")))])
    d = e.advance()
    while d is not None and d["player"] == 0:
        e.answer([keys(d).index("pass")] if "pass" in keys(d) else [0])
        d = e.advance()
    assert e.chars(by(e, "R069"))["power"] == 2000


def battle(rr, use):
    """R069 が、タップされた相手の R070（パワー4000）を攻撃する。R068 は待機中のダイナモ。"""
    e = setup(rr, {"bz": ["R068", "R069"]}, {"bz": ["R070"]})
    e.s.cards[e.bz_tops(1)[0]].tapped = True
    d = to_attack(e)
    e.answer([keys(d).index("attack:R069:R070")])
    d = e.advance()
    if d is not None and d["kind"] == "block":
        e.answer([keys(d).index("no_block")])
        d = e.advance()
    assert d["kind"] == "yes_no"        # バトルが始まる時: R068 をタップするか
    e.answer([0 if use else 1])
    e.advance()
    return e


def test_battle_start_trigger_boosts_the_battling_dynamo(rr):
    """バトルが始まる時にタップすると、パワー 2000 + 3000 = 5000 で 4000 の相手に勝つ。"""
    e = battle(rr, True)
    assert [e.s.cards[c].defn for c in e.bz_tops(1)] == []
    assert by(e, "R069") is not None


def test_battle_start_declined_loses(rr):
    e = battle(rr, False)
    assert [e.s.cards[c].defn for c in e.bz_tops(0)] == ["R068"]
    assert [e.s.cards[c].defn for c in e.bz_tops(1)] == ["R070"]
