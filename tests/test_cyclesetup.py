import pytest

from dmsim.discovery.cyclesetup import setup_from_cycle
from dmsim.engine.scenario import build
from dmsim.engine.zone_graph import Cycle, bundles_of


def test_setup_from_cycle_builds(rules):
    """閉路の札から作った仕込み局面が、実エンジンで組み立てられる（札・ゾーン・マナの形が正しい）。"""
    bs = [b for b in bundles_of(rules) if b.moves][:3]
    if not bs:
        pytest.skip("対象の束がない")
    spec = setup_from_cycle(rules, Cycle(bundles=bs), mana_n=8)
    assert len(spec["p0"]["mana"]) >= 8
    st = build(rules, spec)
    held = {st.s.cards[c].defn for z in ("hand", "graveyard", "bz") for c in st.s.zones[z][0]}
    assert {b.card for b in bs} & held
