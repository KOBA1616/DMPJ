"""tools/fast_loop_screen.py の静的なループ判定が既知コンボの中核を落とさないこと（ふるいの見逃しの確認、2026-11-13）。"""
import os
import sys
from collections import defaultdict
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))


@pytest.fixture(scope="module")
def env():
    # 環境変数は必ず戻す（戻さないと同じワーカーの後のテストが converted.yaml を二重に読み「duplicate card id」になる）
    from dmsim.cards.defs import load_rules
    import loop_cond as C
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        rules = load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old
    by = defaultdict(list)
    for b in C.bundles(rules):
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


def test_hd2_core_passes_with_cond(env):
    """H.D.2. 版の中核（アカシック3＋訪れる魔の時刻＋H.D.2.）: modal の「相手の山札をマナへ」とラスト・バーストの自分を唱える移動を読む。"""
    import fast_loop_screen as F
    rules, by = env
    core = ["dm23ex2-009", "dm23bd7-035", "dmrp07-009"]
    if any(c not in rules.cards for c in core):
        pytest.skip("札が読めない")
    r, cyc = F.judge_set(core, by, rules, strict=True)
    assert r is None, r


def test_cond_reading():
    import loop_cond as C
    ctx = {"net": {"deck": -1, "graveyard": 0}, "opp_net": {}, "inflow": {"graveyard", "hand"}, "inflow_opp": set(),
           "named_in": set(), "draws": True}
    assert C.cond_state({"cmp": [{"count": {"zone": "graveyard", "owner": "you"}}, ">=", 3]}, ctx) == "yes"
    assert C.cond_state({"cmp": [{"count": {"zone": "deck", "owner": "you"}}, "==", 1]}, ctx) == "yes"
    assert C.cond_state({"cmp": [{"count": {"zone": "bz", "owner": "you", "filter": {"name": "X"}}}, ">=", 4]}, ctx) == "no"
    assert C.cond_state({"weird": 1}, ctx) == "unknown"
