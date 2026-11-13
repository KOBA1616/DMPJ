from dmsim.search.reachsearch import fraction, reach_rate, reach_target
from dmsim.engine import Engine


def _game(rules, seed=1):
    return Engine.new_game(rules, [["T001"] * 40, ["T001"] * 40], seed, first_player=0)


def test_reachable_target_from_opening(rules):
    # 通常の開幕から、マナに T001 が2枚（チャージ2回）は2ターン目までに届く
    r = reach_target(_game(rules), {"mana": {"T001": 2}}, width=20, max_depth=30, max_turn=3)
    assert r.reached and r.turn is not None and r.turn <= 6 and fraction(r.engine, 0, {"mana": {"T001": 2}}) == 1.0


def test_unreachable_target_reports_fraction(rules):
    r = reach_target(_game(rules), {"hand": {"NO_SUCH_CARD": 1, "T001": 1}}, width=10, max_depth=10, max_turn=2)
    assert not r.reached and 0.0 < r.best_fraction < 1.0       # 一部（T001）は満たすが全体は届かない


def test_reach_rate_over_seeds(rules):
    out = reach_rate(rules, ["T001"] * 40, {"mana": {"T001": 1}}, [1, 2, 3], width=10, max_depth=20, max_turn=2)
    assert out["rate"] == 1.0 and set(out["reached"]) == {1, 2, 3}


def test_any_wildcard_counts_zone_size(rules):
    from dmsim.search.reachsearch import board_met
    e = _game(rules)
    assert board_met(e, 0, {"shield": {"*": 5}}) and not board_met(e, 0, {"shield": {"*": 6}})
    assert board_met(e, 0, {"hand": {"*": 5}})


def test_shield_under_counts_bundle():
    from dmsim.cards.defs import load_rules
    from dmsim.engine.core import Engine
    from dmsim.search.reachsearch import _have
    e = Engine.new_game(load_rules(), [["T001"] * 40, ["T001"] * 40], 1, first_player=0)
    assert _have(e, 0, "shield_under", "*") == 0


def test_quiet_only_at_top_level_when_settled():
    from dmsim.search.reachsearch import _quiet
    assert _quiet({"kind": "modal"}, False)
    assert not _quiet({"kind": "modal"}, True)
    assert _quiet({"kind": "main"}, True) and _quiet(None, True)


def test_reserve_slots_keep_reachability_and_default_is_unchanged(rules):
    """予約枠(reserve)は幅の一部を次の段に近い局面へ回す。届く目標は届き、reserve=0 は従来と同じ結果。"""
    tg = {"mana": {"T001": 2}}
    base = reach_target(_game(rules), tg, width=6, max_depth=30, max_turn=3)
    same = reach_target(_game(rules), tg, width=6, max_depth=30, max_turn=3, reserve=0, reserve_target={"hand": {"T001": 5}})
    res = reach_target(_game(rules), tg, width=6, max_depth=30, max_turn=3, reserve=2, reserve_target={"hand": {"T001": 5}})
    assert base.reached and res.reached
    assert (same.reached, same.turn, same.nodes) == (base.reached, base.turn, base.nodes)
