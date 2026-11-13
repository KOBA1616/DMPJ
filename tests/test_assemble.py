"""物差しの ① 揃う・④ 速さ（dmsim.eval.assemble）。docs/combo-ruler-design.md §6 タスク6。"""
import os
from types import SimpleNamespace

import pytest

from dmsim.eval import assemble as A
from dmsim.eval import loop_entry as L
from dmsim.eval.ruler import judge
from dmsim.search.game import GameResult


def test_core_need_from_entry_spec():
    assert A.core_need(L.load("saga")) == {"dmrp03-s03": 1, "dm22ex2-021": 2}
    assert A.core_need(L.load("akashic")) == {"dm23ex2-009": 1, "dmrp12-s01": 1, "dm24ex1-038": 1, "dm23bd7-035": 2}


def test_raw_table_monotone():
    t = A.raw_table(L.load("saga"))
    assert 0 < t[3] <= t[4] <= t[6] < 1


def _row(kind=None, turn=None, cards=None, entry=None):
    res = GameResult(seed=0, first_player=0, kind=kind, kill_turn=turn)
    eng = SimpleNamespace(log=[], s=SimpleNamespace(zones={"mana": [[], []]}))
    return {"cards_turn": cards, "entry_turn": entry, "res": res, "verdict": judge(res, eng)}


def test_summarize_columns():
    rows = [_row("direct_attack", 3, 2, None), _row("loop_deck_out", 4, 3, 3), _row("effect", 4, 4, 4), _row()]
    s = A.summarize(rows, ls=L.load("saga"))
    assert s["kill"][3]["kill"] == 1 and s["kill"][3]["beat_win"] == 1
    k4 = s["kill"][4]
    assert (k4["kill"], k4["beat_win"], k4["loop_win"], k4["effect_win"]) == (3, 1, 1, 2)
    assert (k4["effect_loop"], k4["effect_other"]) == (1, 1)      # 効果・山札切れの勝ちをループ由来とそれ以外に分ける
    assert s["cards_by_turn"][3]["k"] == 2 and s["entry_by_turn"][4]["k"] == 2
    assert s["cards_turn_dist"][2] == 1 and "甘く" in s["note"]


@pytest.fixture(scope="module")
def rules():
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        return load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old


def test_run_one_matches_fair_game(rules):
    from dmsim.search.game import fair_game
    ls = L.load("saga")
    r = A.run_one(rules, ls, 3, max_turn=2, budget=40, n_det=2)
    g, _ = fair_game(rules, L.deck_of(ls), ["T001"] * 40, 3, 1, 2, 40, n_det=2)
    assert (r["res"].kill_turn, r["res"].kind, r["res"].decisions) == (g.kill_turn, g.kind, g.decisions)
