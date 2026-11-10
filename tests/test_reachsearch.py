from dmsim.discovery.reachsearch import fraction, reach_rate, reach_target
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
    from dmsim.discovery.reachsearch import board_met
    e = _game(rules)
    assert board_met(e, 0, {"shield": {"*": 5}}) and not board_met(e, 0, {"shield": {"*": 6}})
    assert board_met(e, 0, {"hand": {"*": 5}})
