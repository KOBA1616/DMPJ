"""Rust の crossturn 統合（dmcore の CrossturnSession、増分G）の照合。

run_case を Python 経路とセッション経路で走らせ、結果 dict（判定・
キルターン・総ノード・保持件数・capped・truncated）・キル葉の digest・
手順ログが完全一致することを見る。あわせて trim スコア（value / ruler /
plan）を次ターン候補の局面単位で Python の _trim_score と直接照合する。
登録簿マクロは委譲ゲートに揃えて両側とも無効化する（DMSIM_REGISTRY_MACRO=0）。
"""
import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from dmsim import load_rules
from dmsim.engine import rustcore, scenario as sc
from dmsim.plan.macro import MacroPlanner, load_stage_file

pytestmark = pytest.mark.skipif(not rustcore.enabled(), reason="dmcore 未ビルド/未検証")

ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="module")
def rules():
    return load_rules()


@pytest.fixture()
def ct(monkeypatch):
    import exhaustive_crossturn as ct
    monkeypatch.setenv("DMSIM_REGISTRY_MACRO", "0")
    monkeypatch.delenv("DMSIM_RUST_EXPAND", raising=False)
    monkeypatch.delenv("DMSIM_RUST_CROSSTURN", raising=False)
    ct._PLANNERS = []
    ct._PLAN_PAIR = None
    ct._PLAN_SELECT = "max"
    return ct


def _hidden(seed=1):
    setup = yaml.safe_load(
        (Path(__file__).parent / "saga_hidden_setup.yaml").read_text(encoding="utf-8"))
    setup["seed"] = seed
    return setup


def _run(ct, rules, setup, monkeypatch, use_session, **kw):
    if use_session:
        monkeypatch.setenv("DMSIM_RUST_CROSSTURN", "1")
    else:
        monkeypatch.delenv("DMSIM_RUST_CROSSTURN", raising=False)
    start = sc.build(rules, setup)
    r = ct.run_case(rules, setup, start_engine=start, **kw)
    out = {k: r[k] for k in ("verdict", "kill_turn", "kill_by", "nodes",
                             "frontier_sizes", "capped", "truncated")}
    if r["final"] is not None:
        out["final_digest"] = r["final"].s.digest()
        out["final_log"] = [[e["p"], e["kind"], list(e["choice"])]
                            for e in r["final"].log]
    return out


def test_crossturn_gate_requires_flag(ct, rules, monkeypatch):
    from exhaustive_proto import STAGES, _make_stage_search
    start = sc.build(rules, _hidden(1))
    ts = _make_stage_search(STAGES[0]["stock_offsets"])(0, budget=200_000)
    assert ct._rust_crossturn_open(start, ts, "value") is None
    monkeypatch.setenv("DMSIM_RUST_CROSSTURN", "1")
    assert ct._rust_crossturn_open(start, ts, "value") is not None


def test_crossturn_frontier_matches(ct, rules, monkeypatch):
    kw = dict(max_turn=2, mode="frontier", beam=8, stage=1, order="rank",
              node_budget=200_000, trim_order="value")
    py = _run(ct, rules, _hidden(1), monkeypatch, False, **kw)
    rs = _run(ct, rules, _hidden(1), monkeypatch, True, **kw)
    assert py == rs
    assert py["verdict"] == "kill" and py["kill_turn"] == 2
    assert py["nodes"] == 17330


def test_crossturn_beam_plan_matches(ct, rules, monkeypatch):
    stages, _goal = load_stage_file(ROOT / "tools/saga_loop_stages.yaml")
    ct._PLANNERS = [MacroPlanner(stages=stages)]
    kw = dict(max_turn=3, mode="beam", beam=4, stage=1, order="rank",
              node_budget=200_000, trim_order="plan")
    py = _run(ct, rules, _hidden(1), monkeypatch, False, **kw)
    rs = _run(ct, rules, _hidden(1), monkeypatch, True, **kw)
    assert py == rs
    assert py["verdict"] == "kill" and py["kill_turn"] == 2
    assert py["nodes"] == 5003


def test_trim_score_matches(ct, rules, monkeypatch):
    """hidden seed1 のターン1の次ターン候補15件で trim スコアを直接照合。"""
    from exhaustive_proto import STAGES, _make_stage_search, stage_candidates
    from dmsim.search import turn
    setup = _hidden(1)
    start = sc.build(rules, setup)
    fn, _label = stage_candidates("rank", 1)
    orig = turn.candidates
    turn.candidates = fn
    try:
        ts = _make_stage_search(STAGES[0]["stock_offsets"])(0, budget=200_000)
        nxt = {}

        def handle(_v, leaf, _loops):
            if leaf.s.result is not None:
                return
            e = ct.advance_to_my_turn(leaf)
            if e is not None:
                nxt[e.s.fast_key()] = ct._as_python(e)

        ct.LeafCollector(ts, on_leaf=handle).collect(
            rustcore.maybe_rust(start), 200_000)
    finally:
        turn.candidates = orig
    assert len(nxt) == 15
    stages, _goal = load_stage_file(ROOT / "tools/saga_loop_stages.yaml")
    ct._PLANNERS = [MacroPlanner(stages=stages)]
    for name in ("value", "ruler", "plan"):
        spec = json.dumps(ct._trim_spec(name, 2))
        for eng in nxt.values():
            want = [float(x) for x in ct._trim_score(name, eng, turn=2)]
            got = rustcore.maybe_rust(eng)._c.trim_score(spec)
            assert got == want, (name, got, want)
