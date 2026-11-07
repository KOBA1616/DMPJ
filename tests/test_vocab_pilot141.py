"""語彙パイロット第141弾: power_doubling（パワーを2倍にする）。

新 mod {double_power: true}: op_modify が生成時のパワーを対象ごとに控え、
chars が加算として適用する。エンジン拡張。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def _proto_card():
    with open(Path(__file__).parent.parent / "data/cards/proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == "T170")


def keys(d):
    return [o["key"] for o in d["options"]]


def test_double_power_proto_parses():
    card = parse_card(_proto_card(), TABLES)
    assert card is not None
    assert card.spell[0]["mod"]["double_power"] is True


def test_double_power_behavior(rr):
    """R101 の起動で自分のパワーが 3000 → 6000 になる（ターン継続のため R100 も置く）。"""
    e = setup(rr, {"bz": ["R101", "R100"]}, {"shield": ["R002"]})
    mine = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "R101")
    assert e.chars(mine)["power"] == 3000
    d = e.advance()
    for _ in range(10):
        if d is None:
            break
        if "activate:R101:0" in keys(d):
            e.answer([keys(d).index("activate:R101:0")])
            e.advance()
            break
        e.answer([keys(d).index("pass")] if "pass" in keys(d) else [0])
        d = e.advance()
    else:
        raise AssertionError("activate 決定に到達しなかった")
    assert e.chars(mine)["power"] == 6000
