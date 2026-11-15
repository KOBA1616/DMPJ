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


def test_hand_evolution_stacks_on_card_from_hand(rr):
    """手札進化（evolve_zone: hand）: 手札の水クリーチャーの上に重ねて出す。自分自身は進化元にならない。"""
    e = setup(rr, {"hand": ["R115", "R113"], "mana": ["R113", "R113"]}, {})
    play(e, "R115")
    top = next(c for c in e.s.cards if c.defn == "R115")
    assert top.zone == "bz" and [e.s.cards[u].defn for u in top.under] == ["R113"]


def test_hand_evolution_needs_another_card(rr):
    """手札に他の水クリーチャーが無ければ出せない（出す選択肢が無いので判断なしでターンが進む）。"""
    e = setup(rr, {"hand": ["R115"], "mana": ["R113", "R113"]}, {})
    for _ in range(10):
        d = e.advance()
        if d is None:
            break
        ks = [o["key"] for o in d["options"]]
        assert "play:R115" not in ks
        e.answer([ks.index("pass")] if "pass" in ks else [0])
    assert next(c for c in e.s.cards if c.defn == "R115").zone == "hand"


def test_opp_mana_enters_tapped(rr):
    """opp_mana_tapped を持つクリーチャーがいる間、相手がマナに置いたカードはタップされている。自分のは影響なし。"""
    e = setup(rr, {"hand": ["R113"]}, {"bz": ["R116"]})
    d = e.advance()
    assert d["kind"] == "charge"
    e.answer([[o["key"] for o in d["options"]].index("charge:R113")])
    e.advance()
    m = [c for c in e.s.cards if c.zone == "mana" and c.owner == 0]
    assert m and all(c.tapped for c in m)
    e2 = setup(rr, {"hand": ["R113"], "bz": ["R116"]}, {})
    d = e2.advance()
    e2.answer([[o["key"] for o in d["options"]].index("charge:R113")])
    e2.advance()
    assert not any(c.tapped for c in e2.s.cards if c.zone == "mana" and c.owner == 0)
