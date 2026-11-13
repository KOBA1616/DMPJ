"""速さの上限の静的な見積もり（eval.speed_bound）。既知コンボでの値と、読めない軽減は不明になること。"""
import json

from dmsim.eval import speed_bound as S


def _rules():
    import os
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        return load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old


def test_known_bounds():
    r = _rules()
    assert S.static_bound(r, ["dm25ex3-028", "dm25ex3-055"])["turn"] == 5          # 騎士3 + DMC5
    akashic = json.load(open("data/loops/entry/akashic.json"))["minimal"]
    assert S.static_bound(r, ["dm23ex2-009", "dm23bd7-035", "dmrp12-s01", "dm24ex1-038"], S.bz_need_of_entry(akashic))["turn"] == 10
    saga = json.load(open("data/loops/entry/saga.json"))["minimal"]
    b = S.static_bound(r, ["dm22ex2-021", "dmrp03-s03", "dm22ex1-007"], S.bz_need_of_entry(saga))
    assert b["turn"] is None and "cost_reduce_per_evo" in str(b["unknown"])         # 進化元の数で決まる軽減は読まない


def test_feasible_packing():
    assert S._feasible([3, 2], 3) and not S._feasible([3, 3], 3) and S._feasible([3, 3], 4)
