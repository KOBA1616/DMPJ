"""LoopSpec から作った評価開始局面: 残りの手順を再生すると勝つ。調整用のみ・未確認の印・検証専用は拒否。"""
from pathlib import Path

import pytest

from dmsim import load_rules
from dmsim.eval import evalstarts, replay
from dmsim.base.loopspec import LoopSpec

PATH = Path(__file__).parent.parent / "data" / "loops" / "tenmon_initial.json"


def _prepare(e):
    ts, fa = "dm23ex2-cho018", "dm31-025"
    dk = e.s.zones["deck"][0]
    e.s.zones["deck"][0][:] = sorted(dk, key=lambda c: (e.s.cards[c].defn != ts, e.s.cards[c].defn != fa))


def test_starts_replay_to_a_win_and_are_marked():
    rules = load_rules()
    ls = LoopSpec.from_json(PATH.read_text())
    starts = evalstarts.make_starts(rules, ls, approved={"T013"}, levels=[20])
    assert len(starts) == 1 and starts[0]["split"] == "tuning"
    s = starts[0]
    assert s["remaining"] >= 20 and not s["use_for_primary"] and "dm31-025" in s["unverified"]
    steps = evalstarts._steps(ls)
    assert replay.replay_test(rules, steps[len(steps) - s["remaining"]:])(s["spec"])
    ok = evalstarts.make_starts(rules, ls, approved=set(rules.cards), levels=[20])[0]
    assert ok["use_for_primary"] and ok["unverified"] == []


def test_validation_split_is_refused():
    rules = load_rules()
    ls = LoopSpec.from_json(PATH.read_text())
    with pytest.raises(ValueError):
        evalstarts.make_starts(rules, ls, set(), split="validation")
