from collections import Counter

from dmsim.autofix.usage import detect_prep_ids, played_defs, unused_cards


def U(avail, played):
    return {"avail": Counter(avail), "played": Counter(played), "games": 10}


def test_unused_and_fair_gap():
    fair = U({"a": 10, "b": 10, "c": 10, "d": 2}, {"a": 1, "b": 9, "c": 4})
    cheat = U({"a": 10, "b": 10, "c": 10}, {"a": 8, "b": 9, "c": 9})
    got = {x["id"]: x["reason"] for x in unused_cards(fair, cheat)}
    assert got == {"a": "unused", "c": "fair_gap"}               # b は使われている、d は機会が少ない
    assert detect_prep_ids(fair) == ("a",)                        # ずるい側なしなら unused だけ


def test_played_defs():
    log = [{"p": 0, "kind": "main", "keys": ["play:x:0"]}, {"p": 1, "kind": "main", "keys": ["play:y"]},
           {"p": 0, "kind": "charge", "keys": ["charge:z"]}, {"p": 0, "kind": "main", "keys": ["pass"]}]
    assert played_defs(log, 0) == {"x"}


def test_collect_usage_runs(rules):
    from dmsim.autofix.usage import collect_usage
    u = collect_usage(rules, ["T001", "T073"] * 20, ["T001"] * 40, [1, 2], False, 2, 20)
    assert u["games"] == 2 and sum(u["avail"].values()) > 0
    assert all(u["played"][k] <= u["avail"][k] for k in u["played"])
    f = collect_usage(rules, ["T001", "T073"] * 20, ["T001"] * 40, [1], True, 2, 20, n_det=2)
    assert f["games"] == 1
