"""経路の段（search.route_goal）: データから読め、局面ごとに最も後ろの満たした段が数えられる。"""
from dmsim.eval import loop_entry as L
from dmsim.search import route_goal as RG


def test_load_routes():
    for name in ("saga", "akashic"):
        st = RG.load(name)
        assert len(st) == 4 and all(s.weight > 0 and s.preds for s in st)


def test_saga_entry_board_reaches_last_stage():
    import os
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        rules = load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old
    e = L.build(rules, L.load("saga"), 1)
    st = RG.load("saga")
    assert RG.reached(e, st, 0) == 4          # 入口局面は最後の段（入口）を満たす
    assert RG.route_score(e, st, 0) == sum(s.weight for s in st)
