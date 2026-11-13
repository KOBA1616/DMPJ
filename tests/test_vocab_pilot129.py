"""語彙パイロット第129弾: null_breaker（ヌル・ブレイカー）。

「ヌル・ブレイカー（このクリーチャーはシールドを０ブレイクする）」は
keywords.yaml のキーワードとして登録する（新語彙: 静的 mod {breaks: 0}）。
攻撃時のブレイク数選択肢は break_opts で決まるため、0 が唯一の選択肢になる。
"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-nb",
    "name": "試験ヌル獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 3,
    "power": 2000,
    "races": ["テスト"],
    "keywords": ["null_breaker"],
    "text": "ヌル・ブレイカー（このクリーチャーはシールドを０ブレイクする）",
    "abilities": [],
    "source": {"official": "test-nb", "review": "pending"},
}


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def keys(d):
    return [o["key"] for o in d["options"]]


def test_null_breaker_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    assert "null_breaker" in card.keywords


def test_null_breaker_break_opts(rr):
    e = setup(rr, {"bz": ["R092"]}, {})
    cid = e.bz_tops(0)[0]
    assert e.chars(cid)["break_opts"] == [0]


def test_null_breaker_breaks_nothing(rr):
    """R092 がプレイヤーを攻撃: ブレイク数の選択肢は 0 のみで、シールドは割れない。"""
    e = setup(rr, {"bz": ["R092"]}, {})
    shields_before = len(e.s.zones["shield"][1])
    d = e.advance()
    while d["kind"] in ("charge", "main"):
        e.answer([keys(d).index("pass")])
        d = e.advance()
    assert d["kind"] == "attack"
    e.answer([keys(d).index("attack:R092:player")])
    d = e.advance()
    while d is not None and d["kind"] not in ("charge", "main"):
        if d["kind"] == "choose_breaker":
            assert keys(d) == ["breaks:0"], keys(d)
        e.answer([0])
        d = e.advance()
    assert len(e.s.zones["shield"][1]) == shields_before
