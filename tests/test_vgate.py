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
def test_cost_perf_breakdown_and_term(monkeypatch):
    from dmsim.eval import cost_perf
    b = {"hand": 5, "shield": 5, "mana": 0, "grave": 0, "board": 0, "disrupt": 0.0, "lock": 0.0}
    monkeypatch.setattr(cost_perf, "breakdown", lambda e, m: b)
    monkeypatch.setattr(cost_perf, "mana_used", lambda e, m: 3)
    monkeypatch.setattr(cost_perf, "zone_of", lambda e, z, m: [0] * 5)
    assert cost_perf.performance(None, 0) == 5 * 5.0 + 5 * 10.0
    assert abs(cost_perf.cost_perf(None, 0, scale=2.0) - 2.0 * 75.0 / 4) < 1e-9   # 分母 = 1 + 使用マナ3


def test_lock_recur_classification():
    from types import SimpleNamespace as NS
    from dmsim.eval.lock_terms import is_drain_spell, is_recursion_engine
    gio = NS(types=["creature"], spell=[], abilities=[{"kind": "trigger", "when": {"event": "turn_end"}, "effect": [
        {"op": "move", "select": {"zone": "graveyard", "owner": "you", "filter": {"types": ["spell"]}}, "to": "hand"}]}])
    drill = NS(types=["spell"], abilities=[], spell=[
        {"op": "move", "select": {"zone": "mana", "owner": "opp", "count": 1}, "to": "graveyard"}])
    assert is_recursion_engine(gio) and not is_drain_spell(gio)
    assert is_drain_spell(drill) and not is_recursion_engine(drill)


def test_stage_files_load():
    from pathlib import Path
    from dmsim.eval.vgate import load_stages
    for p in Path("data/eval/stages").glob("*.yaml"):
        st = load_stages(str(p))
        assert st["stages"] and all("target" in s for s in st["stages"]), p


def test_win_stats_and_key():
    from dmsim.eval.vgate import win_key, win_stats
    a = win_stats({1: 7, 2: 11, 3: None, 4: 9}, early=8)
    assert a["n"] == 4 and a["wins"] == 3 and a["early"] == 1 and a["fastest"] == 7
    b = win_stats({1: 9, 2: 9, 3: 9, 4: 9}, early=8)       # 勝ちは多いが早い勝ちが無い
    assert win_key(a) > win_key(b)                           # 辞書式: 早い勝ちが先
    assert win_stats({1: None})["mean_win_turn"] is None


def test_load_prio(tmp_path):
    from dmsim.eval.vgate import load_prio
    p = tmp_path / "w.yaml"
    p.write_text("saga: {under_w: 0.0, res_w: 0.0, plan_w: 0.0, key_pen: 30.0}\nzero: {under_w: 0, res_w: 0, plan_w: 0, key_pen: 0}\n", encoding="utf-8")
    stages = [{"hand": {"A": 1}}, {"bz": {"B": 1}}]
    assert callable(load_prio("saga", stages, str(p)))
    assert load_prio("zero", stages, str(p)) is None and load_prio("none", stages, str(p)) is None
