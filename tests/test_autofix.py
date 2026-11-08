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


def test_add_parts_proposer():
    import random

    from dmsim import deckplan as D
    from dmsim.deckplan import change as C
    p = D.load("data/deckplans/mono_red_beatdown_v0.yaml")
    chs = C.PROPOSERS["add_parts"](p, random.Random(0), ["PARTX"], n=2)
    assert chs and all(c.ops[1] == ("PARTX", 1) for c in chs)
    assert C.apply(p, chs[0]).size() == 40


def test_finish_stage_proposes_finish_bundle_first():
    from dmsim.autofix.loop import propose
    c = propose("finish", Knobs())
    assert c[0][0].finish_mult == 1.0 and "締めの束" in c[0][1]
    assert propose("finish", Knobs(finish_mult=1.0))[0][0].finish_mult == 2.0
    assert all(k.finish_mult <= 8 for k, _ in propose("finish", Knobs(finish_mult=8.0)))


def test_batch_skips_holdout_and_unknown():
    from dmsim.autofix import run_targets
    combos = {"a": {"split": "tuning"}, "h": {"split": "holdout"}}
    r = run_targets([{"combo": "a"}, {"combo": "h"}, {"combo": "zz"}], combos, lambda t: fake, rounds=2)
    assert r[0]["stage"] and "skipped" in r[1] and "skipped" in r[2]


def test_finish_proposes_n_det():
    from dmsim.autofix.loop import propose
    assert any(c.n_det == 8 for c, _ in propose("finish", Knobs()))


def test_store_resumes_and_lookahead(tmp_path):
    from dmsim.autofix import run_targets
    st = tmp_path / "k.yaml"
    run_targets([{"combo": "a"}], {"a": {"split": "tuning"}}, lambda t: fake, rounds=4, store=str(st))
    assert st.exists()
    from dmsim.autofix.loop import propose
    assert any(c.lookahead == 1 for c, _ in propose("finish", Knobs()))


def test_default_board_uses_all_heavy_parts():
    import yaml

    from dmsim.autofix.batch import default_board
    c = {x["id"]: x for x in yaml.safe_load(open("data/known_combos/combos.yaml", encoding="utf-8"))["combos"]}["saga"]
    b = default_board(c)
    assert b["graveyard"] == {"dm22ex2-021": 1, "dmrp03-s03": 1} and b["hand"] == {"dm22ex2-021": 1, "dm22ex1-007": 1}
