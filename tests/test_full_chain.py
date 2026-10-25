"""koba の一連の筋（タイフーン→サガ→手札通過でドラゲリオンを引く→山札2枚でイザナギ→コダマダンス→ドラゲリオン→勝ち）を
台本で再現する。台本は tools/loopcheck_full_chain.py。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from loopcheck_full_chain import trial  # noqa: E402


@pytest.mark.parametrize("pos", [(0, 1, 2), (3, 5, 7), (6, 9, 12)])
def test_full_chain_wins_by_replacement(rules, pos):
    e = trial(rules, pos)
    assert e.s.result and e.s.result["winner"] == 0 and e.s.result["reason"] == "effect"
