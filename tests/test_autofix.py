import pytest

from dmsim.autofix import Knobs, Rule, autofix, diagnose


def fake(k: Knobs, n=30):
    """coef が大きいほど board 到達、budget が大きいほど kill が増える疑似測定。"""
    board = [2 if i < min(n, int(k.coef * 0.75)) else None for i in range(n)]
    kill = [3 if (b is not None and i < min(n, k.budget // 10)) else None for i, b in enumerate(board)]
    return {"kill": kill, "board": board, "cards": [1] * n}


def test_diagnose_stages():
    n = 10
    assert diagnose({"kill": [None] * n, "board": [None] * n, "cards": [None] * n}, 4).stage == "cards"
    assert diagnose({"kill": [None] * n, "board": [None] * n, "cards": [1] * n}, 4).stage == "board"
    assert diagnose({"kill": [None] * n, "board": [2] * n, "cards": [1] * n}, 4).stage == "finish"
    assert diagnose({"kill": [3] * n, "board": [2] * n, "cards": [1] * n}, 4).stage == "ok"


def test_autofix_improves_and_logs(tmp_path):
    led = tmp_path / "l.jsonl"
    k, hist = autofix(fake, Knobs(coef=10, budget=100), rounds=6, ledger=str(led))
    assert k.coef > 10 or k.budget > 100
    assert any(t["verdict"] == "accept" for h in hist for t in h.get("tries", []))
    assert led.read_text().count("\n") == len(hist)


def test_guards():
    with pytest.raises(ValueError):
        autofix(fake, Knobs(), combo={"split": "holdout"})
    _, hist = autofix(fake, Knobs(coef=10), unverified_deck=True)
    assert all(t["verdict"] != "accept" for h in hist for t in h.get("tries", []))
    cards_only = lambda k: {"kill": [None] * 10, "board": [None] * 10, "cards": [None] * 10}
    k, hist = autofix(cards_only, Knobs())
    assert k == Knobs() and "deck_hint" in hist[0]
