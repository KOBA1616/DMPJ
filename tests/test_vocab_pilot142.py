"""語彙パイロット第142弾: draw_event_trigger（引いた時の誘発と枚数条件）。

新式 {drew: {owner: X}}: このターンそのプレイヤーが引いた枚数。
events.py の draw 適用で turn_counters を数える。エンジン拡張。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def _rule_card():
    with open(Path(__file__).parent / "rule_cards.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == "R102")


def test_drew_card_parses():
    card = parse_card(_rule_card(), TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    assert "drew" in str(ab["if"])


def test_drew_counter_and_deny(rr):
    """実際のドローでカウンタが増えることと、2以上で deny が解けることを確認する。"""
    e = setup(rr, {"bz": ["R102"]}, {"shield": ["R002"]})
    mine = e.bz_tops(0)[0]
    assert not e.permits(mine, "attack_player")          # まだ0枚
    e._push(e.ev_task({"ev": "draw", "player": 1}))
    e.advance()
    assert e.s.turn_counters.get("drew:1") == 1          # 実際のドローで数える
    assert not e.permits(mine, "attack_player")          # 1枚ではまだ攻撃不可
    e.s.turn_counters["drew:1"] = 2                      # このターン2枚目を引いた状態にする
    assert e.permits(mine, "attack_player")              # 2枚以上で攻撃可
