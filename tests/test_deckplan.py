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


def test_auto_improve_adopts_and_protects(tmp_path, monkeypatch):
    from dmsim.deckplan import auto as A
    from dmsim.defs import load_rules
    rules = load_rules()
    ids = list(rules.cards)[:10]
    deck = [i for i in ids[1:] for _ in range(4)] + [ids[0]] + [ids[1]] * 0 + [ids[2]] * 0 + [ids[3]] * 0
    deck += [list(rules.cards)[10]] * 3
    combo = {"id": "t", "parts": [{"name": rules.cards[ids[0]].name, "role": "core"}]}
    # 候補に「部品を増やすほど強い」偽の評価を差す
    core = ids[0]
    monkeypatch.setattr(A, "harness_scorer", lambda *a, **k: (lambda d: {(s, 0): (3 if s % 5 >= 4 - d.count(core) else None) for s in range(60)}))
    out = A.auto_improve(rules, deck, [], combo, [], tmp_path / "l.jsonl", rounds=1, kinds=("add_parts",), n=20, out_dir=tmp_path)
    assert out["adopted"] and out["final"] != out["base"]
    import yaml
    saved = yaml.safe_load(open(out["path"], encoding="utf-8"))
    assert sum(e["count"] for e in saved["entries"]) == 40
    base = A.proposal_from_ids(rules, deck)
    assert A.make_resolver(rules)(base.entries[0])[1] == D.CONFIRMED
    assert A.make_resolver(rules)(D.Entry("存在しない札", 1))[1] == D.UNCONVERTED
