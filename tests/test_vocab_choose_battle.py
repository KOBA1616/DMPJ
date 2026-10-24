"""語彙拡張: 相手に選ばれない／選ばれた時（choose）／バトル相手の置換（battle）。"""
from pathlib import Path

import pytest
from conftest import answer, setup

from dmsim.defs import DATA, load_rules

SAMOHAN = "dmrp01-003"
DOTSUKING = "dmrp01-001"


@pytest.fixture(scope="module")
def rr():
    return load_rules(sorted((DATA / "cards").glob("*.yaml")) + [Path(__file__).parent / "rule_cards.yaml"])


def names(e, z, p):
    return sorted(e.s.cards[c].defn for c in e.zlist(z, p))


def bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def test_other_creatures_cannot_be_chosen_by_opponent(rr):
    """サモハンがいる間、相手の効果は自分の他のクリーチャーを選べない。選べるのはサモハンだけ（選択は自動）。"""
    e = setup(rr, {"hand": ["R013"], "mana": ["T008"]}, {"bz": [SAMOHAN, "T001"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:R013")
    d = e.advance()
    assert d["kind"] == "yes_no" and d["player"] == 1                 # サモハンが選ばれた → 2枚引いてもよい
    assert e.chars(bz(e, 1, SAMOHAN))["power"] == 2000                 # 5000 - 3000
    assert e.chars(bz(e, 1, "T001"))["power"] == 2000                  # 選ばれていない（元々2000）


def test_choose_trigger_draws_two_when_chosen(rr):
    e = setup(rr, {"hand": ["R013"], "mana": ["T008"]}, {"bz": [SAMOHAN]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:R013")
    hand = len(e.zlist("hand", 1))
    answer(e, "yes_no", "yes")
    e.advance()
    assert len(e.zlist("hand", 1)) >= hand + 2        # 2枚（その後の自分のドローステップ分を含みうる）


def test_without_samohan_opponent_can_choose_any_creature(rr):
    e = setup(rr, {"hand": ["R013"], "mana": ["T008"]}, {"bz": ["T001", "T004"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:R013")
    d = e.advance()
    assert d["kind"] == "choose_cards" and len(d["options"]) == 2


def test_dotsuking_substitutes_for_joker_being_attacked(rr):
    """自分のターンにジョーカーズでタップ中の相手クリーチャーを攻撃 → ドツキングが身代わりにバトル。"""
    e = setup(rr, {"bz": ["R018", DOTSUKING]}, {"bz": ["T004"]})
    e.s.cards[bz(e, 1, "T004")].tapped = True
    answer(e, "attack", "attack:R018:T004")
    hand = len(e.zlist("hand", 0))
    d = e.advance()
    assert d["kind"] == "choose_replacement"
    e.answer([0])
    e.advance()
    assert "R018" not in names(e, "graveyard", 0)              # ジョーカーズは無傷
    assert names(e, "graveyard", 1) == ["T004"]                # ドツキング 6000 が 3000 に勝つ
    assert DOTSUKING in names(e, "bz", 0)
    assert len(e.zlist("hand", 0)) == hand + 1                 # 勝ったので1枚引く


def test_dotsuking_substitution_can_be_declined(rr):
    e = setup(rr, {"bz": ["R018", DOTSUKING]}, {"bz": ["T004"]})
    e.s.cards[bz(e, 1, "T004")].tapped = True
    answer(e, "attack", "attack:R018:T004")
    d = e.advance()
    e.answer([[o["key"] for o in d["options"]].index("decline")])
    e.advance()
    assert names(e, "graveyard", 0) == ["R018"] and DOTSUKING in names(e, "bz", 0)
