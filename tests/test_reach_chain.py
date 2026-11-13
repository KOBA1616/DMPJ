from dmsim.cards.defs import load_rules
from dmsim.engine.core import Engine
from dmsim.search.reachsearch import reach_chain


def test_chain_stops_at_unreachable_stage():
    rules = load_rules()
    e = Engine.new_game(rules, [["T001"] * 40, ["T001"] * 40], 1, first_player=0)
    r = reach_chain(e, [{"hand": {"*": 1}}, {"shield": {"*": 99}}], width=5, max_depth=3, max_turn=2)
    assert r["stages"] == 1 and len(r["turns"]) == 1


def test_keep_later_keeps_cards_for_later_stages(rules):
    from dmsim.search.reachsearch import _with_keep
    ids = [i for i in rules.cards if i != "T001"][:12]
    deck = (ids * 4)[:40]
    e = Engine.new_game(rules, [deck, ["T001"] * 40], 1, first_player=0)
    held = [i for i in dict.fromkeys(e.s.cards[c].defn for c in e.s.zones["hand"][0])][0]
    stages = [{"bz": {ids[0]: 1}}, {"graveyard": {held: 1}}]
    tg = _with_keep(e, 0, stages, 0)
    assert tg["bz"] == {ids[0]: 1} and tg["hand"][held] >= 1        # 後ろの段が要る手札の札を残す条件が足される
    assert _with_keep(e, 0, stages, 1) == stages[1]                  # 最後の段は変えない


def test_merge_targets():
    from dmsim.search.reachsearch import _merge
    assert _merge({"bz": {"a": 1}, "hand": {"b": 1}}, {"bz": {"a": 2, "c": 1}, "graveyard": {"d": 1}}) == \
        {"bz": {"a": 2, "c": 1}, "hand": {"b": 1}, "graveyard": {"d": 1}}


def test_keep_excludes_cards_in_current_stage(rules):
    from dmsim.search.reachsearch import _with_keep
    ids = [i for i in rules.cards if i != "T001"][:12]
    deck = (ids * 4)[:40]
    e = Engine.new_game(rules, [deck, ["T001"] * 40], 1, first_player=0)
    held = e.s.cards[e.s.zones["hand"][0][0]].defn
    stages = [{"graveyard": {held: 1}}, {"bz": {held: 1}}]
    assert "hand" not in _with_keep(e, 0, stages, 0)          # この段の目標に出る札を手札に残す矛盾は作らない


def test_chain_lookahead_prefers_merging_when_single_steps_dead_end(rules, monkeypatch):
    """単独で1段ずつ進むと次で詰まる局面では、先読みが『次段と合わせる』手を選ぶ。"""
    from dmsim.search import reachsearch as R
    from dmsim.search.reachsearch import ReachResult
    e = Engine.new_game(rules, [["T001"] * 40, ["T001"] * 40], 1, first_player=0)
    stages = [{"hand": {"a": 1}}, {"hand": {"b": 1}}, {"hand": {"c": 1}}]
    calls = []

    def fake(eng, target, me=0, **kw):
        calls.append(target)
        merged = {"hand": {"b": 1, "c": 1}}
        ok = target in (stages[0], merged) or target.get("hand", {}).get("a") == 1
        return ReachResult(ok, 1, eng if ok else None, 1, 1.0 if ok else 0.0)
    monkeypatch.setattr(R, "reach_target", fake)
    r = R.reach_chain(e, stages, 0, keep_later=True)
    assert r["stages"] == 3                           # 段0 → （段1・段2を合わせて）
    assert {"hand": {"b": 1}} not in calls or r["stages"] == 3


def test_reach_set_prefers_specific_stages_and_orders_by_turn(monkeypatch):
    from types import SimpleNamespace as NS
    from dmsim.search import reachsearch as rs
    stages = [{"hand": {"*": 8}}, {"bz": {"A": 1}}, {"graveyard": {"B": 1}}]
    turns = {0: 3, 1: 9, 2: 7}      # 枚数だけの段が一番早く届く

    def fake_target(eng, tg, me, **kw):
        j = stages.index({k: v for k, v in tg.items() if k != "hand"} or tg) if tg in stages else next(
            i for i, s in enumerate(stages) if all(z in tg for z in s))
        return NS(reached=True, turn=turns[j], engine=eng, nodes=1)
    monkeypatch.setattr(rs, "reach_target", fake_target)
    monkeypatch.setattr(rs, "_have", lambda *a, **k: 0)
    out = rs.reach_set(object(), stages, 0)
    assert out["order"] == [2, 1, 0]     # 札を指定した段を先（早い順）、枚数だけの段は最後
