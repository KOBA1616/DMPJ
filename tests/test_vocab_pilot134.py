"""語彙パイロット第134弾: entered_this_turn_filter（このターン中に出た）。

新フィルタ entered_this_turn: true を実装した。判定は entered_turn（バトルゾーンに
出たターン、それ以外は -1）が現在のターンと一致するか。
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
    return next(c for c in data["cards"] if c["id"] == "T167")


def test_entered_this_turn_proto_parses():
    card = parse_card(_proto_card(), TABLES)
    assert card is not None
    assert card.spell[0]["select"]["filter"]["entered_this_turn"] is True


def test_entered_this_turn_filter_match(rr):
    """entered_turn が現在のターンと一致するカードだけが filter に一致する。"""
    e = setup(rr, {"bz": ["R077"]}, {"bz": ["R078"]})
    f = {"entered_this_turn": True}
    mine = e.bz_tops(0)[0]
    assert not e.filter_match(mine, f)       # 初期配置は前のターンからいる
    e.s.cards[mine].entered_turn = e.s.turn  # このターンに出たことにする
    assert e.filter_match(mine, f)
    assert not e.filter_match(mine, {"entered_this_turn": False})
