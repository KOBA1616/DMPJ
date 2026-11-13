"""語彙パイロット第122弾: battle_opponent_filter（バトルの相手で絞る battle_power / battle_indestructible）。

「『ブロッカー』を持つクリーチャーとバトル中、パワーを+Nする」は
mod: {battle_power: {amount: N, opponent_filter: {keyword: blocker}}}、
「火のクリーチャーとバトル中、破壊されない」は
mod: {battle_indestructible: {opponent_filter: {civs: [fire]}}} で表す（エンジン拡張）。
combat._battle が相手を渡し、フィルタに合う時だけ適用する。
"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    files = card_yaml_files() + [str(Path(__file__).parent / "rule_cards.yaml")]
    return load_rules(files)


def keys(d):
    return [o["key"] for o in d["options"]]

CARD_BP = {
    "id": "test-bof1",
    "name": "試験対壁獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "「ブロッカー」を持つクリーチャーとバトル中、このクリーチャーのパワーを+5000する。",
    "abilities": [
        {"kind": "static", "affects": "self",
         "mod": {"battle_power": {"amount": 5000, "opponent_filter": {"keyword": "blocker"}}}},
    ],
    "source": {"official": "test-bof1", "review": "pending"},
}

CARD_BI = {
    "id": "test-bof2",
    "name": "試験対炎不壊獣",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 3,
    "power": 2000,
    "races": ["テスト"],
    "text": "このクリーチャーは、火のクリーチャーとバトル中、破壊されない。",
    "abilities": [
        {"kind": "static", "affects": "self",
         "mod": {"battle_indestructible": {"opponent_filter": {"civs": ["fire"]}}}},
    ],
    "source": {"official": "test-bof2", "review": "pending"},
}


def test_battle_opponent_filter_parses():
    for card in (CARD_BP, CARD_BI):
        parsed = parse_card(card, TABLES)
        assert parsed is not None
    assert CARD_BP["abilities"][0]["mod"]["battle_power"]["opponent_filter"] == {"keyword": "blocker"}


def test_battle_indestructible_bad_value_rejected():
    bad = dict(CARD_BI, id="test-bof-bad")
    bad["abilities"] = [{"kind": "static", "affects": "self",
                         "mod": {"battle_indestructible": {"foo": 1}}}]
    try:
        parse_card(bad, TABLES)
        assert False, "should have raised"
    except Exception as e:
        assert "battle_indestructible" in str(e)


def to_attack(e):
    d = e.advance()
    while d["kind"] in ("charge", "main"):
        e.answer([keys(d).index("pass")])
        d = e.advance()
    assert d["kind"] == "attack", d["kind"]
    return d


def do_battle(e, key):
    d = to_attack(e)
    e.answer([keys(d).index(key)])
    d = e.advance()
    if d is not None and d["kind"] == "block":
        e.answer([keys(d).index("no_block")])
        d = e.advance()
    while d is not None and d["kind"] not in ("charge", "main", "attack"):
        e.answer([0])
        d = e.advance()


def test_battle_power_vs_blocker(rr):
    """R084（3000、対ブロッカー+5000）がタップした R057（ブロッカー5000）を攻撃: 8000で勝つ。"""
    e = setup(rr, {"bz": ["R084"]}, {"bz": ["R057"]})
    e.s.cards[e.bz_tops(1)[0]].tapped = True
    do_battle(e, "attack:R084:R057")
    assert [c.defn for c in e.s.cards if c.zone == "bz" and c.owner == 0] == ["R084"]
    assert e.bz_tops(1) == []          # R057 は破壊された


def test_battle_power_vs_non_blocker(rr):
    """R084 がタップした R070（4000、ブロッカーなし）を攻撃: 修整なしで 3000 < 4000 で負ける。"""
    e = setup(rr, {"bz": ["R084"]}, {"bz": ["R070"]})
    e.s.cards[e.bz_tops(1)[0]].tapped = True
    do_battle(e, "attack:R084:R070")
    assert e.bz_tops(0) == []          # R084 は破壊された


def test_battle_indestructible_vs_fire(rr):
    """タップした R085（2000）が R086（火4000）に攻撃される: 火とのバトルでは破壊されない。"""
    e = setup(rr, {"bz": ["R086"]}, {"bz": ["R085"]})
    e.s.cards[e.bz_tops(1)[0]].tapped = True
    do_battle(e, "attack:R086:R085")
    assert [c.defn for c in e.s.cards if c.zone == "bz" and c.owner == 1] == ["R085"]


def test_battle_indestructible_vs_nature(rr):
    """タップした R085 が R070（自然4000）に攻撃される: フィルタ外なので破壊される。"""
    e = setup(rr, {"bz": ["R070"]}, {"bz": ["R085"]})
    e.s.cards[e.bz_tops(1)[0]].tapped = True
    do_battle(e, "attack:R070:R085")
    assert e.bz_tops(1) == []          # R085 は破壊された
