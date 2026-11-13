"""語彙拡張: 強制 mod.require（506.1b 攻撃しなければならない、507.1b ブロックしなければならない）。"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def keys(d):
    return [o["key"] for o in d["options"]]


def next_dec(e):
    """マナチャージ・メインの選択は飛ばして、次の決定まで進める。"""
    d = e.advance()
    while d is not None and d["kind"] in ("charge", "main"):
        e.answer([keys(d).index("pass")])
        d = e.advance()
    return d


def bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def test_forced_attacker_cannot_pass(rr):
    """506.1b 攻撃を強制されたクリーチャーがいる間は、攻撃せずにステップを終えられない。"""
    e = setup(rr, {"bz": ["R056", "T001"]})
    d = next_dec(e)
    assert d["kind"] == "attack" and "pass" not in keys(d)
    e.answer([keys(d).index("attack:R056:player")])           # 強制の働いたクリーチャーで攻撃
    d = next_dec(e)
    while d["kind"] == "choose_shields":                      # 相手のシールドが割れる（選択は自動で進める）
        e.answer([0])
        d = next_dec(e)
    assert d["kind"] == "attack" and "pass" in keys(d)         # 攻撃済み（タップ）なので強制は終わる


def test_forced_attacker_that_cannot_attack_does_not_block_pass(rr):
    """攻撃できない（召喚酔い）なら強制は働かない。"""
    e = setup(rr, {"bz": ["R056", "T001"]})
    e.s.cards[bz(e, 0, "R056")].entered_turn = e.s.turn
    e.s.cards[bz(e, 0, "T001")].entered_turn = e.s.turn
    d = e.advance()
    assert d["player"] == 1                                   # 攻撃できるものが無いので、強制は働かず攻撃ステップは飛ばされる


def test_forced_blocker_must_block(rr):
    """507.1b ブロックを強制されたクリーチャーがブロックできるなら、「ブロックしない」は選べない（選択肢が1つだけなので自動でブロックする）。"""
    e = setup(rr, {"bz": ["T001"]}, {"bz": ["R057"]})
    d = next_dec(e)
    e.answer([keys(d).index("attack:T001:player")])
    d = e.advance()
    assert d is None or d["kind"] != "block"                  # 選ぶ場面が出ない
    assert len(e.zlist("shield", 1)) == 5                     # ブロックされたのでシールドは割れていない
    assert not any(e.s.cards[c].defn == "T001" for c in e.bz_tops(0))   # パワー2000は5000に負けた


def test_rule_convert_must_attack_and_must_block():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import rule_convert
    base = {"card_type": "クリーチャー", "civilization": "火", "cost": "1", "power": "1000", "race": "X", "mana": "1"}
    a = rule_convert.convert({**base, "id": "x-1", "text": "このクリーチャーは、毎ターン攻撃しなければならない。"})
    assert a["abilities"] == [{"kind": "static", "affects": "self", "mod": {"require": ["attack"]}}]
    b = rule_convert.convert({**base, "id": "x-2", "text": "相手のクリーチャーが攻撃する時、このクリーチャーは可能であればブロックする。"})
    assert b["abilities"][0]["mod"] == {"require": ["block"]}
