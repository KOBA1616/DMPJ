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


def test_cost_perf_breakdown_and_term(monkeypatch):
    from dmsim.eval import cost_perf
    b = {"hand": 5, "shield": 5, "mana": 0, "grave": 0, "board": 0, "disrupt": 0.0, "lock": 0.0}
    monkeypatch.setattr(cost_perf, "breakdown", lambda e, m: b)
    monkeypatch.setattr(cost_perf, "mana_used", lambda e, m: 3)
    monkeypatch.setattr(cost_perf, "zone_of", lambda e, z, m: [0] * 5)
    assert cost_perf.performance(None, 0) == 5 * 5.0 + 5 * 10.0
    assert abs(cost_perf.cost_perf(None, 0, scale=2.0) - 2.0 * 75.0 / 4) < 1e-9   # 分母 = 1 + 使用マナ3
