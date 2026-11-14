"""組の寄与（eval.contrib）と相手の抵抗 段階2（search.opponent.resistance）の確認（2026-11-14）。"""
import pytest

from dmsim.eval.contrib import paired, remove_pair
from dmsim.search.opponent import RESIST_LEVELS, resistance


def test_paired_diff_and_counts():
    w = {1: 1, 2: 1, 3: 0, 4: 1}
    wo = {1: 0, 2: 1, 3: 0, 4: 0, 5: 1}          # 5 は対がないので数えない
    p = paired(w, wo)
    assert p["n"] == 4 and p["diff"] == 0.5 and (p["better"], p["worse"], p["tie"]) == (2, 0, 2)
    assert p["ci95"][0] <= 0.5 <= p["ci95"][1]
    assert paired({}, {})["n"] == 0


def test_remove_pair_uses_most_common_filler():
    d = ["a"] * 4 + ["b"] * 4 + ["f"] * 32
    out = remove_pair(d, ["a", "b"])
    assert out.count("f") == 40 and len(out) == 40
    assert remove_pair(d, ["a"], fill="b").count("b") == 8


def test_level0_and_1_unchanged():
    assert resistance(0)[0] is None
    m, deck = resistance(1)
    assert m.name == "strigger12" and getattr(m, "attack") == "none" and len(deck) == 40


@pytest.mark.parametrize("lv,attack,block", [(2, "all", False), ("2a", "all", False), ("2b", "safe", True)])
def test_level2_models(lv, attack, block):
    m, deck = resistance(lv)
    assert m.name == RESIST_LEVELS[lv] and m.attack == attack and m.block == block and m.play == "all" and m.strigger
    assert len(deck) == 40
