import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import eval_reach  # noqa: E402


def test_reach_monotone_and_bounds():
    p = eval_reach.reach([("A", 4, 1)], [1, 5, 10], trials=3000)
    assert p[1] <= p[5] <= p[10] and 0 <= p[1] and p[10] <= 1
    assert eval_reach.reach([("A", 40, 1)], [1], trials=50)[1] == 1.0


def test_loop_min_start_wins():
    import yaml
    from dmsim.cards.defs import load_rules
    from dmsim.engine.scenario import build
    from dmsim.search.game import play_game
    rules = load_rules()
    if "dm23bd7-035" not in rules.cards:   # オルゼキアは converted.yaml（テストでは読まない）にある
        import pytest
        pytest.skip("converted cards not loaded")
    spec = yaml.safe_load(Path("tools/eval_specs/akashic_loop_min.yaml").read_text(encoding="utf-8"))
    res, _ = play_game(rules, [], [], 1, start=build(rules, spec), max_turn=1, budget=3000, lock_rounds=0)
    assert res.kill_turn == 1 and res.kind == "loop_deck_out"
