"""物差しの陽性対照（dmsim/eval/ruler_control.py）の単体テスト。対局を回す本測定は tools/ruler_control.py（数分かかる）。"""
from collections import Counter

import pytest

from dmsim.eval import loop_entry as le
from dmsim.eval import ruler_control as rc


@pytest.fixture(scope="module")
def rules():
    """実カード（converted.yaml 含む）が要る。他のテストへ影響しないよう環境変数を戻す（test_loop_entry と同じ）。"""
    import os
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        return load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old


def _rows(vals, start=True):
    return [{"seed": i, "start": f"s{i}" if start else "s", "stage2": v, "error": None} for i, v in enumerate(vals)]


def test_judge_pass_and_fail_reasons():
    known = {"a": _rows([1] * 8), "b": _rows([1] * 7 + [0])}
    rnd = [{"combo": "a", "old": "x", "new": "y", "rows": _rows([0] * 8)} for _ in range(5)]
    ok, why, s = rc.judge_control(known, rnd)
    assert ok and why == "ok" and s["random_median"] == 0
    ok, why, _ = rc.judge_control({"a": _rows([0, 1] * 4)}, rnd)
    assert not ok and "届かない" in why
    hi = [{"combo": "a", "old": "x", "new": "y", "rows": _rows([1] * 8)} for _ in range(5)]
    ok, why, _ = rc.judge_control(known, hi)
    assert not ok and "区別がない" in why


def test_judge_detects_stuck_and_no_variation():
    same = {"a": _rows([1] * 8)}
    rnd = [{"combo": "a", "old": "x", "new": "y", "rows": _rows([1] * 8)}]
    ok, why, _ = rc.judge_control(same, rnd)
    assert not ok and "張り付いている" in why
    ok, why, _ = rc.judge_control({"a": _rows([1] * 8, start=False)}, [{"combo": "a", "old": "x", "new": "y", "rows": _rows([0] * 8)}])
    assert not ok and "ばらつき" in why


def test_vary_keeps_entry_and_deck(rules):
    for name in rc.KNOWN:
        ls = le.load(name)
        deck = Counter(le.deck_of(ls))
        seen = set()
        for sd in range(1, 6):
            v = rc.vary(rules, ls, sd)
            p0, b0 = v.source["board"]["p0"], ls.source["board"]["p0"]
            for z in ("bz", "graveyard", "mana"):
                assert p0.get(z) == b0.get(z)
            assert len(p0["hand"]) == len(b0["hand"]) and len(p0["shield"]) == len(b0["shield"])
            placed = Counter(i for ids in p0.values() for i in ids)
            assert not placed - deck
            e = le.build(rules, v, sd)
            assert le.unmet(e, v) == []
            seen.add(rc.start_key(e))
        assert len(seen) > 1


def test_randoms_swap_one_core(rules):
    cores = rc.core_ids()
    gs = rc.make_randoms(rules, "saga", per_core=1)
    assert gs
    for g in gs:
        assert g["old"] in cores and g["new"] not in cores
        assert g["old"] not in g["deck"] and g["new"] in g["deck"]
        a, b = rules.cards[g["old"]], rules.cards[g["new"]]
        assert abs((a.cost or 0) - (b.cost or 0)) <= 1 and set(a.civs) & set(b.civs)
        spec = rc._entry_spec(g["spec"], g["deck"], 1)
        assert sum(len(v) for v in spec["p0"].values()) == 40


def test_core_alternatives_and_group_swap(rules):
    ls = le.load("akashic")
    alts = le.core_alternatives(ls)
    assert {"dm23ex2-009": 1, "dm23bd7-035": 2, "dmrp12-s01": 1, "dm24ex1-038": 1} in alts
    assert {"dm23ex2-009": 1, "dm23bd7-035": 2, "dmrp07-009": 1} in alts
    assert le.required_ids(ls) == ["dm23bd7-035", "dm23ex2-009"]
    gs = rc.make_randoms(rules, "akashic", per_core=1)
    win = [g for g in gs if g["group"] == "勝ち手段"]
    assert win and set(win[0]["old"].split("+")) == {"dmrp12-s01", "dm24ex1-038", "dmrp07-009"}
    for o in ("dmrp12-s01", "dm24ex1-038", "dmrp07-009"):
        assert o not in win[0]["deck"]
    cs = rc.removal_cases(rules, "akashic")
    assert {c["old"]: c["expected_drop"] for c in cs}["dmrp07-009"] is False
    assert {c["old"]: c["expected_drop"] for c in cs}["dm23ex2-009"] is True


def test_explanations_hold_and_exclude():
    known = {"a": _rows([1] * 8)}
    low = [{"combo": "a", "old": "x", "new": "y", "rows": _rows([0] * 8)} for _ in range(5)]
    hi = {"combo": "a", "old": "p+q", "new": "r+s", "rows": _rows([1, 0, 0, 0])}
    ok, why, s = rc.judge_control(known, low + [hi], explanations=[])
    assert not ok and why.startswith("保留") and s["pending"]
    ok, why, s = rc.judge_control(known, low + [hi], explanations=[{"combo": "a", "old": ["q", "p"], "label": "a"}])
    assert ok and s["explained"] and len(s["random"]) == 5
    ok, why, s = rc.judge_control(known, low + [hi], explanations=[{"combo": "a", "old": ["p", "q"], "label": "c"}])
    assert not ok and "不具合" in why


def test_judge_removal_reports_mismatch():
    cs = [{"combo": "a", "old": "x", "new": "y", "expected_drop": True, "rows": _rows([1] * 4)},
          {"combo": "a", "old": "z", "new": "y", "expected_drop": False, "rows": _rows([1] * 4)}]
    r = rc.judge_removal(cs)
    assert r[0]["mismatch"] and r[1]["mismatch"] is None


def test_candidates_exclude_reprints(rules):
    cand = rc.candidates(rules, "dm23ex2-009", rc.core_ids())
    assert "dm25ex2-cho005" not in cand and all(rules.cards[c].name != rules.cards["dm23ex2-009"].name for c in cand)
