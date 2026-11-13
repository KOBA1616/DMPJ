import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from loop_enum import cycles_among, lap_ok  # noqa: E402
from dmsim.engine.zone_graph import bundles_of  # noqa: E402


def test_cycles_among_returns_cycles_with_delta(rules):
    """指定カードだけの網から閉路が数えられ、式の判定（lap_ok）が真偽を返す。"""
    cards = sorted({b.card for b in bundles_of(rules) if b.moves})[:30]
    cs = cycles_among(rules, cards, max_len=2)
    for c in cs[:20]:
        assert isinstance(lap_ok(c), bool)
        assert isinstance(c.delta(), dict)


def test_finite_loop_with_clock_gate(rules):
    """時計（ターン終了）で戻す札と、相手のマナを墓地へ送る呪文の組は、有限ループ（周数が在庫で決まる）として数えられる。"""
    from loop_enum import cycles_among, lap_bound
    ids = ["dm16-051", "dm36-015"]
    if not all(i in rules.cards for i in ids):
        pytest.skip("対象のカードがない")
    cs = cycles_among(rules, ids, max_len=3)
    laps = [lap_bound(c) for c in cs]
    assert any(opp and (n or 0) >= 3 for n, opp in laps)
