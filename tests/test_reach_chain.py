from dmsim.defs import load_rules
from dmsim.engine.core import Engine
from dmsim.discovery.reachsearch import reach_chain


def test_chain_stops_at_unreachable_stage():
    rules = load_rules()
    e = Engine.new_game(rules, [["T001"] * 40, ["T001"] * 40], 1, first_player=0)
    r = reach_chain(e, [{"hand": {"*": 1}}, {"shield": {"*": 99}}], width=5, max_depth=3, max_turn=2)
    assert r["stages"] == 1 and len(r["turns"]) == 1


def test_keep_later_keeps_cards_for_later_stages(rules):
    from dmsim.discovery.reachsearch import _with_keep
    ids = [i for i in rules.cards if i != "T001"][:12]
    deck = (ids * 4)[:40]
    e = Engine.new_game(rules, [deck, ["T001"] * 40], 1, first_player=0)
    held = [i for i in dict.fromkeys(e.s.cards[c].defn for c in e.s.zones["hand"][0])][0]
    stages = [{"bz": {ids[0]: 1}}, {"graveyard": {held: 1}}]
    tg = _with_keep(e, 0, stages, 0)
    assert tg["bz"] == {ids[0]: 1} and tg["hand"][held] >= 1        # 後ろの段が要る手札の札を残す条件が足される
    assert _with_keep(e, 0, stages, 1) == stages[1]                  # 最後の段は変えない


def test_merge_targets():
    from dmsim.discovery.reachsearch import _merge
    assert _merge({"bz": {"a": 1}, "hand": {"b": 1}}, {"bz": {"a": 2, "c": 1}, "graveyard": {"d": 1}}) == \
        {"bz": {"a": 2, "c": 1}, "hand": {"b": 1}, "graveyard": {"d": 1}}


def test_keep_excludes_cards_in_current_stage(rules):
    from dmsim.discovery.reachsearch import _with_keep
    ids = [i for i in rules.cards if i != "T001"][:12]
    deck = (ids * 4)[:40]
    e = Engine.new_game(rules, [deck, ["T001"] * 40], 1, first_player=0)
    held = e.s.cards[e.s.zones["hand"][0][0]].defn
    stages = [{"graveyard": {held: 1}}, {"bz": {held: 1}}]
    assert "hand" not in _with_keep(e, 0, stages, 0)          # この段の目標に出る札を手札に残す矛盾は作らない
