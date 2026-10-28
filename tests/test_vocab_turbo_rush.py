"""語彙拡張: ターボラッシュ（break イベントに「誰がブレイクしたか」を持たせ、自分の他のクリーチャーのブレイクで印を付ける）。"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def keys(d):
    return [o["key"] for o in d["options"]]


def step(e, key):
    """今の決定で key を選ぶ。マナチャージ・メイン・シールド選択は先に処理する。"""
    d = e.advance()
    while d is not None and d["kind"] in ("charge", "main", "choose_shields"):
        e.answer([keys(d).index("pass")] if "pass" in keys(d) else [0])
        d = e.advance()
    e.answer([keys(d).index(key)])


def hand(e):
    return len(e.zlist("hand", 0))


def attack_twice(rr, first, second):
    e = setup(rr, {"bz": ["T001", "R059"]})
    step(e, first)
    d = e.advance()
    while d is not None and d["kind"] == "choose_shields":
        e.answer([0])
        d = e.advance()
    h = hand(e)
    e.answer([keys(d).index(second)])
    e.advance()
    return hand(e) - h


def test_turbo_rush_after_another_creature_breaks_a_shield(rr):
    """他のクリーチャーがシールドをブレイクしたあとなら、ターボラッシュの能力（攻撃時に1枚引く）を得ている。"""
    assert attack_twice(rr, "attack:T001:player", "attack:R059:player") == 1


def test_turbo_rush_not_active_without_other_break(rr):
    """他のクリーチャーがブレイクしていなければ、能力は得ていない。"""
    e = setup(rr, {"bz": ["R059"]})
    h = hand(e)
    step(e, "attack:R059:player")
    e.advance()
    assert hand(e) - h <= 0
