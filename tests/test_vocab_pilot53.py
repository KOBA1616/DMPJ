"""語彙パイロット第53弾（フェーズ17）: 起動型コスト {under: N}（メテオバーン「攻撃できる時」形）。

kind: activate のコストに under を書くと、タップせずに「このクリーチャーの下にある
カードをN枚墓地に置く」ことをコストとして攻撃ステップで使える。使用後も
そのクリーチャーは攻撃できる（攻撃の強制を免れる手段にはならない）。
"""
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


def _to_attack(e):
    d = e.advance()
    while d["kind"] in ("charge", "main"):
        if d["kind"] == "main" and "play:R073" in keys(d):
            e.answer([keys(d).index("play:R073")])
        elif "pass" in keys(d):
            e.answer([keys(d).index("pass")])
        else:
            e.answer(list(range(d["min"])))
        d = e.advance()
        while d["kind"] == "pay_mana":
            e.answer([0])
            d = e.advance()
        if d["kind"] == "choose_evo_source":
            e.answer([0])
            d = e.advance()
    return d


def test_under_cost_activate(rr):
    """攻撃ステップで起動でき、下のカードが墓地へ行き、相手をタップできる。
    使った後もこのクリーチャーは攻撃でき、下が無くなれば再使用はできない。"""
    e = setup(rr, {"hand": ["R073"], "bz": ["T001"], "mana": ["T001"]}, {"bz": ["T001"]})
    d = _to_attack(e)
    assert d["kind"] == "attack"
    assert "activate:R073:0" in keys(d) and "attack:R073:player" in keys(d)
    e.answer([keys(d).index("activate:R073:0")])
    d = e.advance()
    while d["kind"] not in ("attack",):
        e.answer(list(range(d["min"])))
        d = e.advance()
    top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "R073")
    assert names(e, "graveyard", 0) == ["T001"]          # 下のカード（進化元）が墓地へ
    assert len(e.s.cards[top].under) == 0
    assert not e.s.cards[top].tapped                     # タップしていない
    tgt = next(c for c in e.zlist("bz", 1) if e.s.cards[c].defn == "T001")
    assert e.s.cards[tgt].tapped                         # 相手がタップした
    assert "activate:R073:0" not in keys(d)              # 下が無いので再使用できない
    assert "attack:R073:player" in keys(d)               # それでも攻撃はできる


def test_any_attacker_form(rr):
    """「自分のクリーチャーが攻撃できる時」形: 保持者が攻撃できない状態でも、
    他に攻撃できるクリーチャーがいれば使える。"""
    e = setup(rr, {"bz": ["R074", "T001", "T001"], "mana": ["T001"]}, {"bz": ["T001"]})
    top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "R074")
    base = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T001")
    e.s.cards[base].top_of = top            # 進化元を手で重ねる
    e.s.cards[top].under = [base]
    e.s.cards[top].entered_turn = e.s.turn   # 保持者だけ召喚酔い（このターン出た扱い）
    d = e.advance()
    while d["kind"] in ("charge", "main"):
        e.answer([keys(d).index("pass")])
        d = e.advance()
    assert d["kind"] == "attack"
    assert "attack:R074:player" not in keys(d)  # 本人は攻撃できない
    assert "activate:R074:0" in keys(d)         # それでも起動できる
    hand = len(e.zlist("hand", 0))
    e.answer([keys(d).index("activate:R074:0")])
    d = e.advance()
    while d["kind"] != "attack":
        e.answer(list(range(d["min"])))
        d = e.advance()
    assert names(e, "graveyard", 0) == ["T001"]
    assert len(e.zlist("hand", 0)) == hand + 1
