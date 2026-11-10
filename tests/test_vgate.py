from dmsim.eval import vgate


def test_gate_runs_and_ties_on_trivial_stage(rules):
    ids = [i for i in rules.cards if i != "T001"][:14]
    deck = (ids * 3)[:40]
    keys = ids[:3]
    r = vgate.run_gate(rules, deck, ["T001"] * 40, keys, [{"hand": {"*": 1}}], [1, 2], grid=((3.0, 1.0),), min_n=1, width=5, max_depth=3, max_turn=2)
    assert r["n"] == 2 and r["base_total"] == 2 and r["best"] is None and r["rows"][0]["verdict"] == "tie"


def test_gate_adopts_only_strictly_better(rules, monkeypatch):
    scores = iter([[1, 1], [2, 1], [0, 1]])        # base, 候補A(上回り), 候補B(下回り)
    monkeypatch.setattr(vgate, "chain_score", lambda *a, **k: {"stages": next(scores), "total": 0})
    r = vgate.run_gate(rules, [], [], [], [], [1, 2], grid=((3.0, 1.0), (6.0, 1.0)), min_n=1)
    assert [x["verdict"] for x in r["rows"]] == ["adopt", "worse"] and r["best"]["under_w"] == 3.0


def test_gate_accepts_plan_w_candidate(rules, monkeypatch):
    scores = iter([[1, 1], [2, 2]])
    monkeypatch.setattr(vgate, "chain_score", lambda *a, **k: {"stages": next(scores), "total": 0})
    r = vgate.run_gate(rules, [], [], [], [{"hand": {"*": 1}}], [1, 2], grid=((0.0, 0.0, 1500.0),), min_n=1)
    assert r["best"]["plan_w"] == 1500.0 and r["rows"][0]["verdict"] == "adopt"


def test_stage_path_prefers_handwritten(tmp_path):
    (tmp_path / "a.generated.yaml").write_text("stages: []")
    assert vgate.stage_path("a", str(tmp_path)).endswith("a.generated.yaml")
    (tmp_path / "a.yaml").write_text("stages: []")
    assert vgate.stage_path("a", str(tmp_path)).endswith("a.yaml") and not vgate.stage_path("a", str(tmp_path)).endswith("generated.yaml")
    assert vgate.stage_path("zz", str(tmp_path)) is None


def test_gate_small_n_is_not_adopted(rules, monkeypatch):
    scores = iter([[1, 1], [2, 2]])
    monkeypatch.setattr(vgate, "chain_score", lambda *a, **k: {"stages": next(scores), "total": 0})
    r = vgate.run_gate(rules, [], [], [], [], [1, 2], grid=((3.0, 1.0),))      # n=2 < MIN_ADOPT_N
    assert r["rows"][0]["verdict"] == "small_n" and r["best"] is None


def test_runstd_and_normalized_plan():
    from dmsim.plan.macro import RunStd
    rs = RunStd(floor=1.0, warm=3)
    assert rs.std == 1.0               # 少数のうちは floor
    for x in (0.0, 10.0, 20.0, 30.0):
        rs.add(x)
    assert abs(rs.std - 12.9099) < 1e-3   # 標本標準偏差


def test_accumulate_across_days_reaches_min_n():
    rows = [{"under_w": 3.0, "res_w": 1.0, "plan_w": 0.0, "key_pen": 0.0}]
    acc = {}
    for lo in (1, 5):          # 1日目 seed1-4、2日目 seed5-8（1日では4局で small_n）
        res = {"base_by_seed": {s: 1 for s in range(lo, lo + 4)}, "rows": [{**rows[0], "by_seed": {s: 2 for s in range(lo, lo + 4)}}]}
        vgate.accumulate(acc, res)
        j = vgate.judge_acc(acc, rows, 8)
        if lo == 1:
            assert j["rows"][0]["verdict"] == "small_n" and j["best"] is None and vgate.next_seed(acc) == 5
    assert j["rows"][0]["verdict"] == "adopt" and j["rows"][0]["n"] == 8 and j["best"]["total_n"] == 16


def test_judge_acc_uses_only_common_seeds():
    rows = [{"under_w": 3.0, "res_w": 1.0, "plan_w": 0.0, "key_pen": 0.0}]
    acc = {"base": {1: 1, 2: 1}, "3.0:1.0:0.0:0.0": {2: 1, 3: 5}}
    j = vgate.judge_acc(acc, rows, 1)
    assert j["rows"][0]["n"] == 1 and j["rows"][0]["verdict"] == "tie"
