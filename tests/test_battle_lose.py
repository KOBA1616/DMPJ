"""「バトルに負けた時」（when.event: battle_lose）。パワーで負けた側に誘発し、event.opponent がバトルの相手。"""
from pathlib import Path

import pytest
from conftest import setup
from test_vocab_pilot122 import do_battle

from dmsim.cards.defs import card_yaml_files, load_rules


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [str(Path(__file__).parent / "rule_cards.yaml")])


def test_battle_lose_trigger_moves_opponent_to_mana(rr):
    """R086（4000）がタップした R110（2000）を攻撃: R110 は負けて破壊され、誘発で R086 が持ち主のマナへ。"""
    e = setup(rr, {"bz": ["R086"]}, {"bz": ["R110"]})
    e.s.cards[e.bz_tops(1)[0]].tapped = True
    do_battle(e, "attack:R086:R110")
    assert e.bz_tops(0) == [] and e.bz_tops(1) == []
    assert [c.defn for c in e.s.cards if c.zone == "mana" and c.owner == 0 and c.defn == "R086"] == ["R086"]


def test_battle_win_does_not_fire_lose(rr):
    """R110 が勝つ側（相手 R087 1000）なら誘発しない。"""
    e = setup(rr, {"bz": ["R110"]}, {"bz": ["R087"]})
    e.s.cards[e.bz_tops(1)[0]].tapped = True
    e.s.cards[e.bz_tops(0)[0]].sick = False if hasattr(e.s.cards[e.bz_tops(0)[0]], "sick") else None
    do_battle(e, "attack:R110:R087")
    assert [c.defn for c in e.s.cards if c.zone == "bz" and c.owner == 0] == ["R110"]
    assert not [c for c in e.s.cards if c.zone == "mana" and c.defn == "R110"]


def test_battle_lose_resolves_after_destruction(rr):
    """誘発の解決は破壊の後: 負けた R110 は墓地にある。"""
    e = setup(rr, {"bz": ["R086"]}, {"bz": ["R110"]})
    e.s.cards[e.bz_tops(1)[0]].tapped = True
    do_battle(e, "attack:R086:R110")
    assert [c.zone for c in e.s.cards if c.defn == "R110"] == ["graveyard"]


def test_grant_s_trigger_to_shield_spells(rr):
    """「自分のシールドゾーンにある呪文すべてに『S・トリガー』を与える」は static affects zone: shield ＋ allow: [s_trigger] で書ける。"""
    sp = next(k for k, v in rr.cards.items() if "spell" in v.types and "s_trigger" not in v.keywords)
    on = setup(rr, {"bz": ["R111"], "shield": [sp]}, {})
    off = setup(rr, {"shield": [sp]}, {})
    pick = lambda e: next(i for i, x in enumerate(e.s.cards) if x.zone == "shield" and x.owner == 0)
    assert on.permits(pick(on), "s_trigger") and not off.permits(pick(off), "s_trigger")


def test_neo_cost_reduction_only_when_evolving(rr):
    """NEO進化として召喚するなら2少なく（cost_reduce_per_evo: 2）: 火マナ3枚で、火の R086 の上にだけ出せる。"""
    e = setup(rr, {"bz": ["R086"], "hand": ["R112"], "mana": ["R086", "R086", "R086"]}, {})
    d = e.advance()
    while d["kind"] != "main":
        e.answer([[o["key"] for o in d["options"]].index("pass")])
        d = e.advance()
    ks = [o["key"] for o in d["options"]]
    assert "play:R112:neo" in ks and "play:R112" not in ks
    e.answer([ks.index("play:R112:neo")])
    d = e.advance()
    while d is not None and d["kind"] != "main":
        e.answer([0])
        d = e.advance()
    assert [c.defn for c in e.s.cards if c.zone == "bz" and c.owner == 0 and not c.under_of] == ["R112"] if hasattr(e.s.cards[0], "under_of") else True
    assert [e.s.cards[c].defn for c in e.bz_tops(0)] == ["R112"]
