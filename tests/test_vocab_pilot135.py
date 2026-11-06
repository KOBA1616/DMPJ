"""語彙パイロット第135弾: entered_this_turn_condition（このターン中に出た数での条件）。

「このターン中に自分のクリーチャーがN体以上出ていなければ攻撃できない」は
式 {entered: {owner: you}}（既存、そのまま数が返る）と cmp で表す。新語彙なし。
"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules, load_tables, parse_card
import yaml

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def _rule_card():
    with open(Path(__file__).parent / "rule_cards.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == "R098")


def test_entered_count_card_parses():
    card = parse_card(_rule_card(), TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    assert "entered" in str(ab["if"])


def test_entered_count_deny_lifts(rr):
    """entered カウンタが2未満なら攻撃不可、2以上で攻撃可になる。"""
    e = setup(rr, {"bz": ["R098"]}, {"shield": ["R002"]})
    mine = e.bz_tops(0)[0]
    assert not e.permits(mine, "attack_player")          # まだ0体
    e.s.turn_counters["entered:0"] = [mine, mine]        # このターン2体出たことにする
    assert e.permits(mine, "attack_player")
