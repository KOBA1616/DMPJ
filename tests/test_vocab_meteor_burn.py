"""語彙拡張: 進化GV（進化元をちょうど3体重ねる。801）とメテオバーン（下のカードを墓地に置いてもよい。そうした場合だけ後続の効果）。"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def keys(d):
    return [o["key"] for o in d["options"]]


def names(e, zone, p=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def to_main(e):
    d = e.advance()
    while d["kind"] == "charge":
        e.answer([keys(d).index("pass")])
        d = e.advance()
    return d


def test_gv_needs_exactly_three_bases(rr):
    """進化元が2体しかいなければ実行できない。"""
    e = setup(rr, {"hand": ["R067"], "bz": ["T001"] * 2, "mana": ["T001"]})
    assert "play:R067" not in keys(to_main(e))


def test_gv_stacks_three_bases(rr):
    e = setup(rr, {"hand": ["R067"], "bz": ["T001"] * 4, "mana": ["T001"]})
    d = to_main(e)
    e.answer([keys(d).index("play:R067")])
    d = e.advance()
    while d["kind"] == "pay_mana":
        e.answer([0])
        d = e.advance()
    assert d["kind"] == "choose_evo_source" and d["min"] == d["max"] == 3
    e.answer([0, 1, 2])
    e.advance()
    top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "R067")
    assert len(e.s.cards[top].under) == 3
    assert [e.s.cards[c].defn for c in e.bz_tops(0)].count("T001") == 1                  # 重ねなかった1体は残る


def attack_with_burn(rr, say_yes=True):
    e = setup(rr, {"hand": ["R067"], "bz": ["T001"] * 3, "mana": ["T001"]}, {"bz": ["T001"]})
    d = to_main(e)
    e.answer([keys(d).index("play:R067")])
    d = e.advance()
    while d["kind"] == "pay_mana":
        e.answer([0])
        d = e.advance()
    d = e.advance() if d is None else d                        # 進化元がちょうど3体なら選択は出ない
    e.answer([keys(d).index("attack:R067:player")])
    d = e.advance()
    assert d["kind"] == "yes_no"
    e.answer([0 if say_yes else 1])
    d = e.advance()
    if say_yes:
        assert d["kind"] == "choose_cards"                     # 下のカードのどれを墓地に置くか
        e.answer([0])
        e.advance()
    return e


def test_meteor_burn_pays_and_resolves(rr):
    """下のカードを墓地に置いたので、パワー4000以下のクリーチャー（相手のものも）がすべて破壊される。"""
    e = attack_with_burn(rr)
    assert names(e, "graveyard", 0) == ["T001"]               # 墓地に置いた1枚（下の残りは破壊されない）
    assert names(e, "graveyard", 1) == ["T001"]               # 破壊された相手の1体
    assert e.bz_tops(1) == []                                  # 相手の T001 も破壊された
    assert [e.s.cards[c].defn for c in e.bz_tops(0)] == ["R067"]


def test_meteor_burn_declined(rr):
    e = attack_with_burn(rr, say_yes=False)
    assert len(e.bz_tops(1)) == 1 and names(e, "graveyard", 0) == [] and names(e, "graveyard", 1) == []


def test_meteor_burn_needs_a_card_under(rr):
    """下にカードがなければ墓地に置けないので、「そうした場合」以降は行わない。"""
    e = setup(rr, {"bz": ["R067"]}, {"bz": ["T001"]})
    d = to_main(e)
    e.answer([keys(d).index("attack:R067:player")])
    d = e.advance()
    assert d["kind"] == "yes_no"
    e.answer([0])
    e.advance()
    assert len(e.bz_tops(1)) == 1
