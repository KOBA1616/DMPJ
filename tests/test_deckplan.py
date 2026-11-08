from dmsim import deckplan as D
from dmsim.deckplan import change as C
from dmsim.deckplan.evaluate import AcceptRule, decide
from dmsim.deckplan.spec import from_dict
import random


def test_record_and_check():
    p = D.load("data/deckplans/mono_red_beatdown_v0.yaml")
    r = D.check(p)
    assert r["issues"] == [] and r["unverified"] and p.size() == 40
    d = p.to_dict(); d["future_field"] = 1
    assert from_dict(d).to_dict()["future_field"] == 1   # 未知項目は保持
    d["schema_version"] = 99
    try:
        from_dict(d); assert False
    except ValueError:
        pass


def test_limit_and_swap():
    p = D.load("data/deckplans/mono_red_beatdown_v0.yaml")
    ch = C.Change("swap", [("こたつむり", -1), ("X", 1)])
    q = C.apply(p, ch)
    assert q.size() == 40 and q.plan_id() != p.plan_id()
    try:
        C.apply(p, C.Change("swap", [("こたつむり", -1), ("カンゴク入道", 1)])); assert False
    except ValueError:
        pass
    assert C.PROPOSERS["swap"](p, random.Random(0), ["X", "Y"], n=3)


def test_decide_rules():
    rule = AcceptRule(turn=3)
    base = {(s, 0): None for s in range(40)}
    cand = {(s, 0): 3 for s in range(40)}
    assert decide(base, cand, rule, False)["verdict"] == "accept"
    assert decide(base, cand, rule, True)["verdict"] == "hold_unverified"
    assert decide(cand, base, rule, False)["verdict"] == "reject"
    assert decide(base, base, rule, False)["verdict"] == "inconclusive"
    assert decide(base, {(0, 0): 1}, rule, False)["verdict"] == "invalid"


def test_improve_loop_with_fake_scorer(tmp_path):
    p = D.load("data/deckplans/mono_red_beatdown_v0.yaml")
    res = lambda e: ("id_" + e.name, D.CONFIRMED)
    def scorer(ids):                       # こたつむりを減らすほど強い、という偽の評価
        n = ids.count("id_こたつむり")
        return {(s, 0): (3 if s % 4 >= n else None) for s in range(40)}
    out = D.improve(p, scorer, res, ["Y"], tmp_path / "l.jsonl", rounds=2, seed=1, n=20, rule=AcceptRule(turn=3))
    assert (tmp_path / "l.jsonl").read_text().count("\n") > 0
    assert out.size() == 40
