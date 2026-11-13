"""ロック勝ちを最後まで確かめる（dmsim.eval.lockcheck.run_lock_to_end、P2 タスク3）。"""
from conftest import setup

from dmsim.eval.lockcheck import lock_probe, make_full_lock_judge, prefer_policy, run_lock_to_end
from dmsim.search.game import play_game


def _locked(rules, deck_left):
    e = setup(rules, {"bz": ["T021"]}, deck_size=40, deck_left=deck_left)   # 毎ターン相手のマナを全部墓地へ
    e.advance()
    return e


def test_lock_runs_to_opponent_deck_out(rules):
    e = _locked(rules, [30, 12])
    assert lock_probe(e, 0) is not None
    run = run_lock_to_end(e, 0)
    assert run.won and run.broken is None
    assert run.result == {"winner": 0, "reason": "deck_out", "turn": run.result["turn"]}
    assert (run.set_turn, run.win_turn, run.turns_to_win) == (1, 12, 11)
    assert run.own_deck_left == 19
    assert e.s.result is None                 # 元の局面は進めない（clone で回す）


def test_own_deck_runs_out_first(rules):
    run = run_lock_to_end(_locked(rules, [5, 30]), 0)
    assert not run.won and run.own_deck_left == 0
    assert run.broken.startswith("自分が先に尽きた") and run.result["winner"] == 1


def test_lock_broken_when_opponent_resources_grow(rules):
    run = run_lock_to_end(setup(rules, {"bz": ["T001"]}, deck_size=40, deck_left=[30, 12]), 0)
    assert not run.won and run.broken.startswith("相手の資源が増えた")
    assert run.opp_growth.get("mana:1", 0) > 0 and run.broken_turn == 3   # 基準は一巡後の2ターン目、3ターン目に増加を検出


def test_turn_cap(rules):
    run = run_lock_to_end(_locked(rules, [30, 30]), 0, max_turns=3)
    assert not run.won and run.broken == "3 ターン以内に終わらない" and run.broken_turn == 5


def test_prefer_policy_falls_back_to_passive(rules):
    pol = prefer_policy("play:NOPE")
    d = {"options": [{"key": "charge:T001"}, {"key": "pass"}], "min": 0}
    assert pol(None, d) == [1]
    assert prefer_policy("charge:")(None, d) == [0]


def test_full_lock_judge_plugs_into_play_game(rules):
    """lock_judge に差し込むと、最後まで勝てるロックだけを lock と記録する（既定の判定役は変えない）。"""
    e = setup(rules, {"hand": ["T021"], "mana": ["T008"] * 6}, deck_size=40, deck_left=[30, 12])
    res, _ = play_game(rules, None, None, 1, start=e, budget=50, lock_judge=make_full_lock_judge())
    assert (res.kill_turn, res.kind) == (1, "lock")
    e = setup(rules, {"hand": ["T021"], "mana": ["T008"] * 6}, deck_size=40, deck_left=[5, 30])
    res, _ = play_game(rules, None, None, 1, max_turn=1, start=e, budget=50, lock_judge=make_full_lock_judge())
    assert res.kind != "lock"
