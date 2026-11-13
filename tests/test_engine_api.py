"""エンジン疑似API（dmsim.engine_api）: 従来の Engine の使い方と同じ結果になり、fork・巻き戻し・差分検証が働くこと。"""
import pytest

from dmsim.engine import api
from dmsim.cards.defs import load_rules
from dmsim.engine.core import Engine


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _decks(rules):
    ids = sorted(i for i in rules.cards if i.startswith("dm"))
    d = [ids[i % len(ids)] for i in range(40)]
    return [d, list(d)]


def _spec(rules, seed=3):
    return {"kind": "new_game", "decks": _decks(rules), "seed": seed, "first_player": 0}


def test_apply_matches_plain_engine(rules):
    s = api.Session.open(rules, _spec(rules))
    e = Engine.new_game(rules, _decks(rules), 3, 0)
    for _ in range(60):
        d, de = s.decision(), e.advance()
        if d is None:
            assert de is None
            break
        assert {k: v for k, v in d.items() if k != "id"} == de
        r = s.apply([0], digest=True)
        e.answer([0])
        e.advance()
        assert r["digest"] == e.s.digest()


def test_fork_is_independent_and_rollback(rules):
    s = api.Session.open(rules, _spec(rules))
    s.decision()
    c = s.checkpoint()
    d0 = s.digest()
    f = s.fork()
    f.apply([0])
    assert s.digest() == d0 and f.digest() != d0
    s.apply([0])
    assert s.digest() != d0
    s.rollback(c)
    assert s.digest() == d0


def test_apply_by_keys_and_expand(rules):
    s = api.Session.open(rules, _spec(rules))
    d = s.decision()
    key = d["options"][-1]["key"]
    fa, fb = s.fork(), s.fork()
    fa.apply({"keys": [key]})
    fb.apply([len(d["options"]) - 1])
    assert fa.digest() == fb.digest()
    kids = s.expand()
    assert len(kids) == len(d["options"]) and all(k["session"].eng is not s.eng for k in kids)


def test_observe_hides_hidden_cards(rules):
    s = api.Session.open(rules, _spec(rules))
    s.decision()
    st = s.observe("player:0")
    hidden = [c for c in st["cards"] if c["defn"] is None]
    assert hidden and all(c["zone"] in ("deck", "shield", "hand") for c in hidden)
    assert all(c["defn"] is not None for c in st["cards"] if c["zone"] == "hand" and c["owner"] == 0)


def test_lockstep_identical_runs_agree_and_detects_divergence(rules):
    # 同一実装どうしは最後まで一致する（決定性の自己検証）
    a, b = api.Session.open(rules, _spec(rules)), api.Session.open(rules, _spec(rules))
    r = api.lockstep(a, b, "random:5", max_decisions=100000)
    assert r["ok"] and r["divergence"] is None and r["steps"] > 10
    # 違う seed は digest の差として検出される
    c = api.Session.open(rules, _spec(rules, seed=4))
    out = api.diff_states(a.observe(), c.observe())
    assert out and all({"path", "a", "b"} <= set(x) for x in out)


def test_lockstep_reports_first_divergence(rules):
    a = api.Session.open(rules, _spec(rules, seed=3))
    b = api.Session.open(rules, _spec(rules, seed=4))
    r = api.lockstep(a, b, "first", max_decisions=50)
    assert r["ok"] is False and r["divergence"]["at"] in ("decision", "digest")
