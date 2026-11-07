"""語彙パイロット第103弾: linked_god_filter（リンクしているゴッド）。

新フィルタ linked_god: true を実装した。「進化クリーチャーまたはリンクしているゴッド」は
any_of [{evolution: true}, {linked_god: true}] で表す。リンク判定は link_side（リンク位置の
キーワードを持つゴッド）かつ link_members が2体以上。
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
    return next(c for c in data["cards"] if c["id"] == "T157")


def test_linked_god_proto_parses():
    card = parse_card(_proto_card(), TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"


def test_linked_god_filter_match(rr):
    """R079/R080 をリンクさせると linked_god に一致し、単独では一致しない。"""
    e = setup(rr, {"bz": ["R079", "R080"]}, {"bz": []})
    tops = e.bz_tops(0)
    assert len(tops) == 2
    f = {"linked_god": True}
    assert not any(e.filter_match(c, f) for c in tops)   # 未リンク
    for c in tops:
        e.s.cards[c].link = 1                            # 同一グループでリンク
    assert all(e.filter_match(c, f) for c in tops)
    assert not e.filter_match(tops[0], {"linked_god": False})
