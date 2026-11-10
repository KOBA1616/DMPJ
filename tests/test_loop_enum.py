import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from loop_enum import cycles_among, lap_ok  # noqa: E402
from dmsim.zone_graph import bundles_of  # noqa: E402


def test_cycles_among_returns_cycles_with_delta(rules):
    """指定カードだけの網から閉路が数えられ、式の判定（lap_ok）が真偽を返す。"""
    cards = sorted({b.card for b in bundles_of(rules) if b.moves})[:30]
    cs = cycles_among(rules, cards, max_len=2)
    for c in cs[:20]:
        assert isinstance(lap_ok(c), bool)
        assert isinstance(c.delta(), dict)
