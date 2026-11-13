"""語彙パイロット第140弾: same_name_as_chosen_card（選んだカードと同じ名前）。

新式 {name_of: {ref: X}} を eval_expr に追加した。フィルタでは
{name: {name_of: {ref: X}}} と書き、candidates が選択時に名前へ解決する。
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


def _proto_card():
    with open(Path(__file__).parent.parent / "data/cards/proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == "T169")


def test_name_of_proto_parses():
    card = parse_card(_proto_card(), TABLES)
    assert card is not None
    assert card.spell[1]["select"]["filter"]["name"] == {"name_of": {"ref": "picked"}}


def test_name_of_candidates(rr):
    """同じ名前の2体だけが候補になり、別名の1体は候補にならない。"""
    e = setup(rr, {"bz": ["R077", "R077", "R078"]}, {"shield": ["R002"]})
    tops = e.bz_tops(0)
    assert len(tops) == 3
    picked = next(c for c in tops if e.s.cards[c].defn == "R077")
    env = {"you": 0, "vars": {"picked": [e.s.ref(picked)]}}
    sel = {"zone": "bz", "owner": "you",
           "filter": {"types": ["creature"], "name": {"name_of": {"ref": "picked"}}}}
    got = e.candidates(sel, env)
    assert len(got) == 2
    assert all(e.s.cards[c].defn == "R077" for c in got)
