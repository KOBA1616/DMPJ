"""語彙パイロット第126弾: power_less_than_self（自分よりパワーが小さい相手）。

「パワーがこのクリーチャーより小さい相手のクリーチャー」は第116弾の
filter {power_le: {sum: [{power_of: {ref: self}}, -1]}} で表す。
「パワーがこのクリーチャーより小さいクリーチャーにブロックされない」は
mod {deny: [{action: be_blocked, other: {power_le: <同式>}}]} で表す（エンジン拡張:
permits の other フィルタの式を許可側カード基準で前評価する）。
"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()
LESS_THAN_SELF = {"power_le": {"sum": [{"power_of": {"ref": "self"}}, -1]}}

CARD = {
    "id": "test-pls",
    "name": "試験統率獣",
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 6,
    "power": 5000,
    "races": ["テスト"],
    "text": "このクリーチャーは、パワーがこのクリーチャーより小さいクリーチャーにブロックされない。",
    "abilities": [
        {"kind": "static", "affects": "self",
         "mod": {"deny": [{"action": "be_blocked", "other": LESS_THAN_SELF}]}},
    ],
    "source": {"official": "test-pls", "review": "pending"},
}

CARD2 = {
    "id": "test-pls2",
    "name": "試験強撃砲士",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 4,
    "power": 4000,
    "races": ["テスト"],
    "text": "このクリーチャーが攻撃する時、パワーがこのクリーチャーより小さい相手のクリーチャーを１体破壊する。",
    "abilities": [
        {"kind": "trigger", "when": {"event": "attack", "subject": "self"},
         "effect": [
             {"op": "destroy", "select": {"zone": "bz", "owner": "opp", "count": 1, "filter": LESS_THAN_SELF}},
         ]},
    ],
    "source": {"official": "test-pls2", "review": "pending"},
}


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def keys(d):
    return [o["key"] for o in d["options"]]


def test_power_less_than_self_parses():
    for card in (CARD, CARD2):
        assert parse_card(card, TABLES) is not None


def to_attack(e):
    d = e.advance()
    while d["kind"] in ("charge", "main"):
        e.answer([keys(d).index("pass")])
        d = e.advance()
    assert d["kind"] == "attack", d["kind"]
    return d


def attack_player(e, key):
    d = to_attack(e)
    e.answer([keys(d).index(key)])
    return e.advance()


def test_weaker_blocker_cannot_block(rr):
    """R089（5000）がプレイヤーを攻撃: R068（ブロッカー3000）はブロックできない（選択肢に出ない）。"""
    e = setup(rr, {"bz": ["R089"]}, {"bz": ["R068"]})
    d = attack_player(e, "attack:R089:player")
    if d is not None and d["kind"] == "block":
        assert not any("R068" in k for k in keys(d)), keys(d)
        e.answer([keys(d).index("no_block")])


def test_equal_blocker_can_block(rr):
    """R057（ブロッカー5000、可能ならブロック必須）は R089（5000）と等しいのでブロックし、相打ちになる。"""
    e = setup(rr, {"bz": ["R089"]}, {"bz": ["R057"]})
    d = attack_player(e, "attack:R089:player")
    while d is not None and d["kind"] not in ("charge", "main"):
        if d["kind"] == "block":
            e.answer([next(i for i, k in enumerate(keys(d)) if "R057" in k)])
        else:
            e.answer([0])
        d = e.advance()
    assert e.bz_tops(0) == [] and e.bz_tops(1) == []   # 5000 vs 5000 で相打ち
