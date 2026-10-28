"""語彙拡張: 攻撃された時（when.target）・ブロックされた時（when.attacker）の誘発と、event.target / event.attacker 参照。"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def keys(d):
    return [o["key"] for o in d["options"]]


def first_attack_decision(e):
    d = e.advance()
    while d is not None and d["kind"] in ("charge", "main"):
        e.answer([keys(d).index("pass")])
        d = e.advance()
    return d


def bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def test_this_creature_attacked_trigger(rr):
    """攻撃先がこのクリーチャーの時だけ誘発する。"""
    e = setup(rr, {"bz": ["T001"]}, {"bz": ["R060"]})
    e.s.cards[bz(e, 1, "R060")].tapped = True
    d = first_attack_decision(e)
    hand = len(e.zlist("hand", 1))
    e.answer([keys(d).index("attack:T001:R060")])
    e.advance()
    assert len(e.zlist("hand", 1)) >= hand + 1


def test_own_other_creature_attacked_trigger_and_event_target_ref(rr):
    """自分の他のクリーチャーが攻撃された時に誘発し、event.target で攻撃された側を指せる（攻撃された側だけ+1000）。"""
    e = setup(rr, {"bz": ["T001"]}, {"bz": ["R060", "R060"]})
    for c in e.bz_tops(1):
        e.s.cards[c].tapped = True
    d = first_attack_decision(e)
    e.answer([keys(d).index("attack:T001:R060")])
    d = e.advance()
    while d is not None and d["kind"] == "order_pending":     # 2つの誘発（攻撃されたクリーチャー自身と、もう1体）の解決順
        e.answer([0])
        d = e.advance()
    assert sorted(e.chars(c)["power"] for c in e.bz_tops(1)) == [5000, 6000]


def test_blocked_trigger(rr):
    """ブロックされた時、攻撃クリーチャー自身の誘発が働く。"""
    e = setup(rr, {"bz": ["R061"]}, {"bz": ["R057"]})
    d = first_attack_decision(e)
    hand = len(e.zlist("hand", 0))
    e.answer([keys(d).index("attack:R061:player")])
    e.advance()
    assert len(e.zlist("hand", 0)) >= hand + 1
