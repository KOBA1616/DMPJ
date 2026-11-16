"""FAIR の対局でもループを記録する（P2 案 F）。手順・勝敗は変えず、記録の欄だけが増える。"""
import pytest

from dmsim.eval import loop_entry as L
from dmsim.eval.lockcheck import lock_probe  # noqa: F401  既定のロック判定役を登録する
from dmsim.eval.ruler import judge
from dmsim.search.game import GameResult, fair_game, record_turn_loops
from dmsim.search.turn import TurnSearch


@pytest.fixture(scope="module")
def rules():
    import os
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        return load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old


def _choices(e):
    return [(x["p"], x["kind"], tuple(x["keys"])) for x in e.log]


@pytest.mark.parametrize("name", ["saga", "akashic"])
@pytest.mark.slow
def test_recording_does_not_change_moves(rules, name):
    # 記録あり・なし・ロック判定ありで、同じ seed の手順と勝敗が一致する
    ls = L.load(name)
    for sd in (0, 1):
        a, ea = fair_game(rules, L.deck_of(ls), ["T001"] * 40, sd, sd % 2, 3, 40, n_det=2, pattern_loops=False)
        b, eb = fair_game(rules, L.deck_of(ls), ["T001"] * 40, sd, sd % 2, 3, 40, n_det=2)
        c, ec = fair_game(rules, L.deck_of(ls), ["T001"] * 40, sd, sd % 2, 3, 40, n_det=2,
                          lock_judge=lambda e, me, r: None, lock_rounds=2)
        assert _choices(ea) == _choices(eb) == _choices(ec)
        assert (a.kind, a.kill_turn, a.lost, a.decisions) == (b.kind, b.kill_turn, b.lost, b.decisions) == (c.kind, c.kill_turn, c.lost, c.decisions)


def test_fair_game_lock_judge_is_called_only_when_asked(rules):
    ls = L.load("saga")
    calls = []

    def spy(e, me, r):
        calls.append(r)
        return None
    fair_game(rules, L.deck_of(ls), ["T001"] * 40, 0, 0, 2, 20, n_det=1, lock_judge=spy)
    assert calls == []                                    # 既定 lock_rounds=0 は呼ばない（従来どおり）
    fair_game(rules, L.deck_of(ls), ["T001"] * 40, 0, 0, 2, 20, n_det=1, lock_judge=spy, lock_rounds=2)
    assert calls and set(calls) == {2}


def test_record_turn_loops_detects_pattern_from_executed_log(rules):
    # サガ入口で実際に指した手順（ここでは CHEAT の探索で作る）に、FAIR と同じ記録関数がパターン検出をかける
    ls = L.load("saga")
    start = L.build(rules, ls, 0)
    d = start.advance()
    assert d is not None
    after, _ = TurnSearch(0, 200).run(start)
    res = GameResult(seed=0, first_player=0)
    record_turn_loops(res, start, after, len(start.log), [], [], 1, 0)
    lps = [lp for lp in res.loops if lp["source"] == "pattern"]
    assert lps and lps[0]["laps"] >= 3 and lps[0]["own_turn"] == 1
    assert judge(res, after).stage1.ok


def test_fair_certificate_plan_is_recorded_once():
    from dmsim.search.fair import FairTurnSearch
    fs = FairTurnSearch(0)
    lp = {"kind": "kill", "length": 4, "win_by": "opp_deck_out", "delta": {"deck:1": -1}, "source": "certificate", "verified": True}
    fs._plans = {("a",): [lp]}
    fs._record_plan(("a",), 0)
    fs._record_plan(("a",), 1)
    fs._record_plan(("b",), 2)
    assert len(fs.chosen) == 1 and fs.chosen[0]["evidence"] == "determinized" and fs.chosen[0]["decision"] == 0
