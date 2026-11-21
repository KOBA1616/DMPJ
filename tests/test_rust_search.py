"""Rust のターン内展開ループ（dmcore の expand_turn、増分E・段階1）の照合。

段階1の範囲は「ループ検出なし・チェックポイントなし」の LeafCollector 走査。
Python ループ側も検出器をスタブに差し替えて同じ意味論に揃え、ノード数・
truncated・葉 digest の多重集合・葉の評価の多重集合が完全一致することを見る。
登録簿マクロは段階1の対象外なので、両側とも無効化して揃える
（DMSIM_REGISTRY_MACRO=0。委譲ゲートもマクロが空の場合だけ通る）。
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from dmsim import load_rules
from dmsim.engine import rustcore, scenario as sc
from dmsim.engine.loop import abstract
from dmsim.search import turn
from dmsim.search.turn import TurnSearch

pytestmark = pytest.mark.skipif(not rustcore.enabled(), reason="dmcore 未ビルド/未検証")


class _NoDet:
    """検出器のスタブ（段階1の意味論: observe は常に None）。"""

    @classmethod
    def new(cls, eng, me, draw_discard=None):
        return cls()

    def fork(self):
        return self

    def observe(self, eng):
        return None


@pytest.fixture(scope="module")
def rules():
    return load_rules()


@pytest.fixture()
def no_detectors(monkeypatch):
    import exhaustive_crossturn as ct
    monkeypatch.setattr(ct, "Detectors", _NoDet)
    monkeypatch.setenv("DMSIM_REGISTRY_MACRO", "0")
    return ct


def _hidden_setup(seed=1):
    from pathlib import Path
    setup = yaml.safe_load(
        (Path(__file__).parent / "saga_hidden_setup.yaml").read_text(encoding="utf-8"))
    setup["seed"] = seed
    return setup


def _collect(ct, rules, setup, ts, budget, use_rust, monkeypatch):
    if use_rust:
        monkeypatch.setenv("DMSIM_RUST_EXPAND", "1")
    else:
        monkeypatch.delenv("DMSIM_RUST_EXPAND", raising=False)
    got = []

    def on_leaf(v, leaf, loops):
        got.append((v, leaf.s.digest()))

    eng = rustcore.maybe_rust(sc.build(rules, setup))
    assert isinstance(eng, rustcore.RustEngine)
    _l, trunc, nodes = ct.LeafCollector(ts, on_leaf=on_leaf).collect(eng, budget)
    return nodes, trunc, got


def _assert_same(a, b):
    assert a[0] == b[0], f"nodes: py={a[0]} rust={b[0]}"
    assert a[1] == b[1], f"truncated: py={a[1]} rust={b[1]}"
    assert Counter(d for _v, d in a[2]) == Counter(d for _v, d in b[2]), "葉 digest の多重集合"
    assert Counter(v for v, _d in a[2]) == Counter(v for v, _d in b[2]), "葉の評価の多重集合"


def test_abstract_hash_matches(rules):
    """骨格ハッシュ（abstract）が Python と一致する（tkey の土台）。"""
    setup = _hidden_setup(1)
    eng = rustcore.maybe_rust(sc.build(rules, setup))
    assert isinstance(eng, rustcore.RustEngine)
    zc = {z: bool(zd["counter"]) for z, zd in rules.zones.items()}
    zcj = json.dumps(zc)
    from dmsim.search.turn import candidates, charge_only_policy
    from dmsim.search.leaf_eval import Weights
    e = eng
    for _ in range(12):
        h_py, _ctr = abstract(e, "in_turn")
        assert e._c.abstract_hash(zcj) == h_py
        d = e.advance()
        if d is None:
            break
        if d["player"] == 0:
            e.answer(candidates(e, d, Weights(), cap=6)[0])
        else:
            e.answer(charge_only_policy(e, d))


def test_expand_stage2_rank_matches(no_detectors, rules, monkeypatch):
    """段2・rank の候補生成での collect が Python ループと完全一致する。"""
    from exhaustive_proto import STAGES, _make_stage_search, stage_candidates
    ct = no_detectors
    st = next(s for s in STAGES if s["stage"] == 2)
    fn, _label = stage_candidates("rank", 2)
    monkeypatch.setattr(turn, "candidates", fn)
    setup = _hidden_setup(1)
    budget = 2000
    a = _collect(ct, rules, setup,
                 _make_stage_search(st["stock_offsets"])(0, budget=budget),
                 budget, False, monkeypatch)
    b = _collect(ct, rules, setup,
                 _make_stage_search(st["stock_offsets"])(0, budget=budget),
                 budget, True, monkeypatch)
    _assert_same(a, b)


def test_expand_default_candidates_matches(no_detectors, rules, monkeypatch):
    """既定の候補生成（turn.candidates）での collect が完全一致する。"""
    ct = no_detectors
    setup = _hidden_setup(1)
    budget = 1500

    def mk():
        ts = TurnSearch(0, budget=budget)
        ts.macros = []   # 段階1のゲート（マクロ空）に合わせる
        return ts

    a = _collect(ct, rules, setup, mk(), budget, False, monkeypatch)
    b = _collect(ct, rules, setup, mk(), budget, True, monkeypatch)
    _assert_same(a, b)


def test_expand_stage1_value_matches(no_detectors, rules, monkeypatch):
    """段1・value（評価順）の候補生成での collect が完全一致する。"""
    from exhaustive_proto import STAGES, _make_stage_search, stage_candidates
    ct = no_detectors
    st = next(s for s in STAGES if s["stage"] == 1)
    fn, _label = stage_candidates("value", 1)
    monkeypatch.setattr(turn, "candidates", fn)
    setup = _hidden_setup(1)
    budget = 1200
    a = _collect(ct, rules, setup,
                 _make_stage_search(st["stock_offsets"])(0, budget=budget),
                 budget, False, monkeypatch)
    b = _collect(ct, rules, setup,
                 _make_stage_search(st["stock_offsets"])(0, budget=budget),
                 budget, True, monkeypatch)
    _assert_same(a, b)


def test_expand_gate_blocks_without_flag(no_detectors, rules, monkeypatch):
    """フラグが無ければ委譲されない（既定の挙動は従来どおり Python ループ）。"""
    ct = no_detectors
    setup = _hidden_setup(1)
    eng = rustcore.maybe_rust(sc.build(rules, setup))
    ts = TurnSearch(0, budget=100)
    ts.macros = []
    monkeypatch.delenv("DMSIM_RUST_EXPAND", raising=False)
    assert ct._rust_expand_params(ct.LeafCollector(ts), eng, 100) is None
    monkeypatch.setenv("DMSIM_RUST_EXPAND", "1")
    assert ct._rust_expand_params(ct.LeafCollector(ts), eng, 100) is not None
