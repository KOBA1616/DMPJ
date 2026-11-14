"""tools/fast_loop_screen.py の静的なループ判定が既知コンボの中核を落とさないこと（ふるいの見逃しの確認、2026-11-13）。"""
import os
import sys
from collections import defaultdict
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))


@pytest.fixture(scope="module")
def env():
    os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    from dmsim.cards.defs import load_rules
    from dmsim.engine import zone_graph as Z
    rules = load_rules()
    by = defaultdict(list)
    for b in Z.bundles_of(rules):
        by[b.card].append(b)
    return rules, by


def test_known_cores_pass_and_reach_by_extension(env):
    import fast_loop_screen as F
    rules, by = env
    if "dm22ex2-021" not in rules.cards or "dm23ex2-009" not in rules.cards:
        pytest.skip("既知コンボの札が読めない")
    out = F.known_check(rules, by, strict=True)
    for n in F.KNOWN:
        assert out[n]["any_pass"], n
        assert out[n]["reach_by_extension"], n


def test_ref_move_and_many_in_net(env):
    import fast_loop_screen as F
    from dmsim.engine.zone_graph import Bundle, Move
    b = Bundle("x", "x", None, [Move("hand", "bz", alias="out"), Move("?", "hand", ref="out")])
    assert F.net([b]) == {}
    c = Bundle("y", "y", None, [Move("hand", "graveyard", True), Move("graveyard", "hand", many=True), Move("hand", "graveyard")])
    assert F.net([c]).get("hand", 0) == 0
