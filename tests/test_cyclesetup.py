from dmsim.discovery.cyclesetup import setup_from_cycle
from dmsim.scenario import build
from dmsim.zone_graph import Cycle, bundles_of


def test_setup_from_cycle_builds_for_known_cores(rules):
    """既知コンボの中核札から作った仕込み局面が、実エンジンで組み立てられる（札・ゾーン・マナの形が正しい）。"""
    bs = bundles_of(rules)
    ids = {"dm16-051", "dm36-015", "dm36-078"}
    cyc = Cycle(bundles=[b for b in bs if b.card in ids])
    spec = setup_from_cycle(rules, cyc, mana_n=8)
    assert len(spec["p0"]["mana"]) >= 8
    st = build(rules, spec)
    held = {st.s.cards[c].defn for z in ("hand", "graveyard") for c in st.s.zones[z][0]}
    assert ids & held
