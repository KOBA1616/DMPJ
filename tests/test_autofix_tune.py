import pytest
from dmsim.autofix.loop import Knobs
from dmsim.autofix.tune import mutate, tune
import random


def fake(k, seeds):
    """coef=40,budget=400 付近でキルが早くなる擬似測定（なめらか。シードごとに決まる揺らぎ付き）。"""
    q = abs(k.coef - 40) / 40 + abs(k.budget - 400) / 400
    out = []
    for s in seeds:
        noise = ((s * 7919) % 13) / 13 * 0.6
        t = 2 + round(q * 2 + noise)
        out.append(t if t <= 4 else None)
    return {"kill": out}


def test_mutate_in_range():
    rng = random.Random(1)
    k = Knobs()
    for _ in range(200):
        k = mutate(k, rng)
        assert 2 <= k.coef <= 100 and 50 <= k.budget <= 1600 and 0 <= k.lookahead <= 2


def test_overlap_rejected():
    with pytest.raises(ValueError):
        tune(fake, Knobs(), [1, 2], [2, 3])


def test_tune_improves_and_logs():
    k0 = Knobs(coef=15.0, budget=200)
    k, hist = tune(fake, k0, list(range(100)), list(range(100, 200)), generations=8, lam=6)
    assert any(h.get("verdict") == "accept" for h in hist)
    s = lambda kk: sum(x is not None for x in fake(kk, range(300, 400))["kill"])
    assert s(k) >= s(k0)


def test_tune_stops_at_deadline_and_keeps_progress():
    import time
    k0 = Knobs(coef=15.0, budget=200)
    k, hist = tune(fake, k0, list(range(100)), list(range(100, 200)), generations=8, lam=6, deadline=time.time() - 1)
    assert hist[-1]["verdict"] == "timeout" and k == k0          # 枠切れなら測定に入らず現状を返す


def test_tune_deadline_midway_returns_accepted_so_far(monkeypatch):
    import time
    import dmsim.autofix.tune as T
    t = {"now": 0.0}
    monkeypatch.setattr(time, "time", lambda: t["now"])
    calls = []

    def slow(k, seeds):
        calls.append(1)
        t["now"] += 1.0                                          # 1測定ごとに1秒進む
        return fake(k, seeds)
    k, hist = T.tune(slow, Knobs(coef=15.0, budget=200), list(range(100)), list(range(100, 200)), generations=8, lam=6, deadline=15.0)
    assert hist[-1]["verdict"] == "timeout" and len(calls) <= 18
