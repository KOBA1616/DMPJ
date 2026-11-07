from dmsim import scenario
from dmsim.search import FairTurnSearch


def _eng(rules, order):
    e = scenario.build(rules, {"p0": {"hand": ["T001", "T073"], "mana": ["T004"] * 4}, "p1": {}, "filler": "T001",
                               "seed": 1, "deck_size": 20, "deck_left": None})
    return e


def _reach_own(e):
    d = e.advance()
    assert d is not None
    return e


def test_runs_turn_and_leaves_input(rules):
    e = _reach_own(_eng(rules, None))
    n = len(e.log)
    out = FairTurnSearch(0, budget=30, n_det=3, seed=1).run(e)
    assert len(e.log) == n and len(out.log) > n


def test_deterministic_for_seed(rules):
    e = _reach_own(_eng(rules, None))
    a = FairTurnSearch(0, budget=30, n_det=3, seed=2).run(e)
    b = FairTurnSearch(0, budget=30, n_det=3, seed=2).run(e)
    assert a.log == b.log


def test_independent_of_true_deck_order(rules):
    """真の山札の並びだけを入れ替えても（観測は同じ）選ぶ手は変わらない。"""
    e1 = _reach_own(_eng(rules, None))
    for p in (0, 1):                      # 山札に種類の違うカードを混ぜる（e1 は上が T073、e2 は下が T073）
        e1.s.cards[e1.s.zones["deck"][p][0]].defn = "T073"
    e2 = e1.clone()
    for p in (0, 1):
        top, bot = e2.s.zones["deck"][p][0], e2.s.zones["deck"][p][-1]
        e2.s.cards[top].defn, e2.s.cards[bot].defn = e2.s.cards[bot].defn, e2.s.cards[top].defn
    a = FairTurnSearch(0, budget=30, n_det=3, seed=4).run(e1)
    b = FairTurnSearch(0, budget=30, n_det=3, seed=4).run(e2)
    assert [x["keys"] for x in a.log] == [x["keys"] for x in b.log]
