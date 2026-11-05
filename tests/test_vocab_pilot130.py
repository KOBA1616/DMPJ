"""語彙パイロット第130弾: crew_breaker（クルー・ブレイカー）。

「クルー・ブレイカー：X（自分の他のX１体につき、シールドをさらにもう１枚ブレイクする）」は
static の mod {breaks: {count: <selector>}} で表す（エンジン拡張: breaks に
{count} 形式を追加し、ブレイク数を 1 + count_of(selector) とする）。
"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-crew",
    "name": "試験クルー竜",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 6,
    "power": 5000,
    "races": ["テスト", "ドラゴン"],
    "text": "クルー・ブレイカー：ドラゴン（このクリーチャーは、バトルゾーンにある自分の他のドラゴン１体につき、シールドをさらにもう１枚ブレイクする）",
    "abilities": [
        {"kind": "static", "affects": "self",
         "mod": {"breaks": {"count": {"zone": "bz", "owner": "you", "other": True,
                                      "filter": {"race_has": "ドラゴン"}}}}},
    ],
    "source": {"official": "test-crew", "review": "pending"},
}


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def test_crew_breaker_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    assert card.abilities[0]["mod"]["breaks"]["count"]["filter"] == {"race_has": "ドラゴン"}


def test_crew_breaker_bad_breaks_rejected():
    bad = dict(CARD, id="test-crew-bad")
    bad["abilities"] = [{"kind": "static", "affects": "self", "mod": {"breaks": {"foo": 1}}}]
    try:
        parse_card(bad, TABLES)
        assert False, "should have raised"
    except Exception as e:
        assert "breaks" in str(e)


def test_crew_breaker_counts_others(rr):
    """他のドラゴンが2体いればブレイク数は 1+2=3、いなければ 1。"""
    e = setup(rr, {"bz": ["R093", "R094", "R094"]}, {})
    cid = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "R093")
    assert e.chars(cid)["break_opts"] == [3]
    e2 = setup(rr, {"bz": ["R093"]}, {})
    cid2 = e2.bz_tops(0)[0]
    assert e2.chars(cid2)["break_opts"] == [1]


def test_breaks_amount_form(rules, rr):
    """既存形式 {amount, count}: 1 + 係数×数（dmd10-008 型）。相手2体で 1+2×2=5。"""
    e = setup(rr, {"bz": ["R095"]}, {"bz": ["R010", "R011"]})
    a = next(i for i, c in enumerate(e.s.cards) if c.defn == "R095")
    assert e.chars(a)["breaks"] == 5


def test_breaks_civ_count_form(rules, rr):
    """既存形式 {civ_count: セレクタ}（第79弾）: 1 + 文明の種類数。相手が自然+水で 3。"""
    e = setup(rr, {"bz": ["R096"]}, {"bz": ["R010", "R012"]})
    a = next(i for i, c in enumerate(e.s.cards) if c.defn == "R096")
    assert e.chars(a)["breaks"] == 3
