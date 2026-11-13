"""デッキ単位の再現性（多色カードは各文明をマナに1枚ずつ。ドローで届く範囲 reach も数える）。"""
import pathlib
import tempfile

import test_dmc_knight as t
from dmsim.eval.reproducibility import play_ready_prob


def _rules():
    return t._small_rules(pathlib.Path(tempfile.mkdtemp()))


def test_hindsight_is_upper_bound_and_monotone_in_turn():
    r = _rules()
    deck = [t.K] * 4 + [t.D] * 4 + ["T001"] * 16 + ["T002"] * 8 + ["T003"] * 8
    p = play_ready_prob(r, deck, t.K, turns=(3, 5, 7), n=600)
    assert p["hindsight"][3] <= p["hindsight"][5] <= p["hindsight"][7]
    for k in (3, 5, 7):
        assert p["online"][k] <= p["hindsight"][k] + 1e-9


def test_reach_by_draw_raises_the_probability_for_a_combo_partner():
    r = _rules()
    deck = [t.K] * 4 + [t.D] * 4 + ["T001"] * 16 + ["T002"] * 8 + ["T003"] * 8
    a = play_ready_prob(r, deck, t.K, turns=(5,), n=800, need=[t.D])
    b = play_ready_prob(r, deck, t.K, turns=(5,), n=800, need=[t.D], reach={t.D: 3})
    assert b["hindsight"][5] >= a["hindsight"][5]
    assert b["online"][5] >= a["online"][5]
