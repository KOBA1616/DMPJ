"""combo_hunt2（dmsim/discovery/hunt2.py）の純粋ロジックのテスト。ルール読み込みはしない。"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.discovery.hunt2 import engine_verdict, grown_of, stratified_sample, stratum_of  # noqa: E402


def test_verdict_win_by():
    assert engine_verdict({"deck:1": -1}, win_by="opp_deck_out") == ("win", True)


def test_verdict_pressure():
    assert engine_verdict({"deck:1": -1, "deck:0": -1}) == ("pressure", True)
    assert engine_verdict({"shield:1": -2}) == ("pressure", True)


def test_verdict_growth():
    assert engine_verdict({"graveyard:0": 1, "deck:0": -1}) == ("growth", True)   # サガ型
    assert engine_verdict({"hand:0": 1, "mana_untapped:0": 1}) == ("growth", True)


def test_verdict_burn():
    assert engine_verdict({"deck:0": -1}) == ("burn", True)


def test_verdict_fatal():
    assert engine_verdict({"hand:0": -1, "graveyard:0": 2}) == (None, False)      # 手札が細る
    assert engine_verdict({"mana:0": -1, "deck:1": -1}) == (None, False)         # マナが細る
    assert engine_verdict({"bz:0": -1}) == (None, False)                          # 場が減るだけ
    assert engine_verdict({"bz:0": -1, "hand:0": 2}) == ("growth", True)         # 補償があればよい


def test_verdict_empty():
    assert engine_verdict({}) == (None, False)
    assert engine_verdict(None) == (None, False)


def test_grown_of():
    assert grown_of({"graveyard:0": 1, "deck:0": -1}) == ["graveyard", "deck_thin"]
    assert grown_of({"hand:0": 2}) == ["hand"]
    assert grown_of({}) == []


def test_stratum_of():
    desc = {"delta": {"graveyard": 1, "deck": -1}, "opp": {}, "steps": ["サガ:trigger:enter:bz"]}
    s = stratum_of(desc)
    assert "graveyard" in s and "trigger" in s


def test_stratified_sample_covers_strata():
    items = [{"stratum": f"s{i % 3}", "score": float(i), "cards": [str(i)]} for i in range(30)]
    picked = stratified_sample(items, 6, random.Random(1))
    assert len(picked) == 6
    assert {p["stratum"] for p in picked} == {"s0", "s1", "s2"}     # 層を巡回するので全層から取れる
    picked_all = stratified_sample([dict(x) for x in items], 100, random.Random(1))
    assert len(picked_all) == 30
