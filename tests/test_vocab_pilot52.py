"""語彙パイロット第52弾（フェーズ17）: S・バックの対象指定を filter に一般化。

従来は文明名（文字列）だけだった面フィールド s_back に filter（辞書）を書けるようにし、
種族指定（S・バック：アウトレイジ等）・複合文明（水または闇）・ツインパクト指定を表す。
ツインパクト指定は filter の twinpact キー（第52弾で追加）で判定する。
"""
from pathlib import Path

import pytest
from conftest import answer, setup

from dmsim.cards.defs import card_yaml_files, load_rules


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def names(e, zone, p=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def attack(rr, hand, shields):
    e = setup(rr, {"bz": ["T005"]}, {"shield": shields, "hand": hand})
    answer(e, "attack", "attack:T005:player")
    d = e.advance()
    assert d["kind"] == "choose_shields"
    e.answer([0, 1])
    return e


def test_s_back_race_form(rr):
    """種族指定: テスト種族のカードが手札に加わる時、それを捨てて無料で召喚できる。"""
    e = attack(rr, ["R071"], ["R060"] * 5)
    d = e.advance()
    assert d["kind"] == "declare_sback" and d["player"] == 1
    assert len(d["options"]) == 2
    e.answer([0])
    e.advance()
    assert "R071" in names(e, "bz", 1)
    assert names(e, "graveyard", 1) == ["R060"]


def test_s_back_multi_civ_form(rr):
    """複合文明指定: 水のカードが手札に加わる時、それを捨てて無料で唱えられる。"""
    e = attack(rr, ["R072"], ["R015"] * 5)
    d = e.advance()
    assert d["kind"] == "declare_sback" and d["player"] == 1
    e.answer([0])
    e.advance()
    assert names(e, "graveyard", 1).count("R072") == 1 and names(e, "graveyard", 1).count("R015") == 1


def test_s_back_multi_civ_no_match(rr):
    """条件に合わないカード（光）しか手札に加わらなければ、S・バックの宣言は出ない。"""
    e = attack(rr, ["R072"], ["R060"] * 5)
    d = e.advance()
    assert d["kind"] != "declare_sback"
    assert "R072" in names(e, "hand", 1)
