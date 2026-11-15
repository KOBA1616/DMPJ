"""「出た時にトリガーする能力を1つ使う」（op: use_cip。Jビッグ・マーダン=ロウなど）。"""
from pathlib import Path

import pytest
from conftest import setup
from test_vocab_pilot5 import play

from dmsim.cards.defs import card_yaml_files, load_rules


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [str(Path(__file__).parent / "rule_cards.yaml")])


def _hand(e, p=0):
    return sum(1 for c in e.s.cards if c.zone == "hand" and c.owner == p)


def test_use_cip_reuses_other_creatures_etb(rr):
    """R113（出た時1枚引く）がいる所で R114 を出す: R113 の能力を使って1枚引く。"""
    e = setup(rr, {"bz": ["R113"], "hand": ["R114"], "mana": ["R113"]}, {})
    h = _hand(e)
    play(e, "R114")
    assert _hand(e) == h


def test_use_cip_without_candidates_does_nothing(rr):
    """他のクリーチャーがいなければ何もしない。R114 自身の use_cip は候補にならない。"""
    e = setup(rr, {"hand": ["R114"], "mana": ["R113"]}, {})
    h = _hand(e)
    play(e, "R114")
    assert _hand(e) == h - 1


def test_use_cip_excludes_abilities_that_use_cip(rr):
    """他の R114（use_cip を含む能力）しかいなければ使えない（Jビッグ以外）。"""
    e = setup(rr, {"bz": ["R114"], "hand": ["R114"], "mana": ["R113"]}, {})
    h = _hand(e)
    play(e, "R114")
    assert _hand(e) == h - 1
