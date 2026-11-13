"""ループ発見（1段目）と勝ち筋探索（2段目）の分離。周回数を変えてストックした局面から勝ちを探す。"""
from pathlib import Path

import yaml

from dmsim.search import loop_first as lf
from dmsim.engine import scenario as sc


def test_two_stage_finds_saga_loop_then_a_win_after_n_cycles(rules, monkeypatch):
    # 2段目でループを回さずに勝つ（案 E で2段目の探索が自分でループを回す）と cycles=0 になるので、ここでは切って見る
    import dmsim.search.turn as T
    monkeypatch.setattr(T, "REPEAT_FIRST", False)
    spec = yaml.safe_load((Path(__file__).parent / "saga_loop_first_setup.yaml").read_text(encoding="utf-8"))
    eng = sc.build(rules, spec)
    found = lf.two_stage(eng, 0, discover_budget=1500, seek_budget=1500)
    assert found and all(f.verified for f in found)                       # 1段目: 見つけたループは再生で確かめ済み
    assert all(f.cert.delta == {"deck:0": -1, "graveyard:0": 1} for f in found)   # サガの1周
    winners = [f for f in found if f.wins]
    assert len(winners) == 1
    assert all(not f.tried for f in found[found.index(winners[0]) + 1:])  # 勝てたところで打ち切る
    assert winners                                                        # 2段目: ストックした局面から勝てる
    w = winners[0].wins[0]
    assert 0 < w["cycles"] <= winners[0].cert.limit and w["reason"] == "effect"
    # 同じ入力から同じ結果になる（決定的）
    again = lf.two_stage(sc.build(rules, spec), 0, 1500, 1500)
    assert [f.wins for f in again] == [f.wins for f in found]
    allw = lf.two_stage(sc.build(rules, spec), 0, 1500, 1500, first_win_only=False)
    assert sum(1 for f in allw if f.wins) >= 1


def test_two_stage_still_wins_with_repeat_first(rules):
    spec = yaml.safe_load((Path(__file__).parent / "saga_loop_first_setup.yaml").read_text(encoding="utf-8"))
    found = lf.two_stage(sc.build(rules, spec), 0, discover_budget=1500, seek_budget=1500)
    assert any(f.wins for f in found)
