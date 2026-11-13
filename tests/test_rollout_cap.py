"""貪欲な先読み(_rollout)が終わらない繰り返しに入ったら、step_limit と同じ扱いで打ち切る。"""
from dmsim.search.turn import TurnSearch


class _S:
    result = None
    turn = 3


class _E:
    def __init__(self):
        self.s = _S()
        self.answers = 0

    def answer(self, c):
        self.answers += 1


def test_rollout_cap_marks_step_limit(monkeypatch):
    ts = TurnSearch.__new__(TurnSearch)
    ts.w = None
    ts.rollout_cap = 5
    monkeypatch.setattr(TurnSearch, "_settle", lambda self, eng: {"player": 0})
    monkeypatch.setattr("dmsim.search.turn.candidates", lambda eng, d, w, cap=1: [[0]])
    e = _E()
    ts._rollout(e)
    assert e.answers == 5
    assert e.s.result == {"winner": None, "reason": "step_limit", "turn": 3}


def test_rollout_normal_untouched(monkeypatch):
    ts = TurnSearch.__new__(TurnSearch)
    ts.w = None
    seq = iter([{"player": 0}, {"player": 0}, None])
    monkeypatch.setattr(TurnSearch, "_settle", lambda self, eng: next(seq))
    monkeypatch.setattr("dmsim.search.turn.candidates", lambda eng, d, w, cap=1: [[0]])
    e = _E()
    ts._rollout(e)
    assert e.answers == 2 and e.s.result is None
