"""物差しの本体 dmsim.eval.ruler（段1・段2）。docs/combo-ruler-design.md §6 タスク5・§8.4。"""
import os
from types import SimpleNamespace

import pytest
import yaml

from dmsim.eval import loop_entry as L
from dmsim.eval.lockcheck import lock_probe
from dmsim.eval.ruler import judge
from dmsim.search.game import GameResult, play_game


def _eng(log, opp_mana=3):
    return SimpleNamespace(log=log, s=SimpleNamespace(zones={"mana": [[], [0] * opp_mana]}))


PAT = {"source": "pattern", "verified": True, "kind": "finite", "laps": 5, "stocked": 5, "delta": {"deck:0": -1},
       "limit_est": 9, "log_start": 0, "log_end": 10, "win_by": None, "own_turn": 3}
ATK = {"kind": "attack", "keys": ["attack:x:player"]}


def test_no_loop_is_stage1_fail():
    v = judge(GameResult(seed=0, first_player=0), _eng([]))
    assert not v.stage1.ok and not v.stage2.ok and "ループが無い" in v.stage1.reason


def test_loop_then_beat_is_beat():
    res = GameResult(seed=0, first_player=0, kind="direct_attack", kill_turn=3, loops=[PAT])
    v = judge(res, _eng([{"kind": "x", "keys": []}] * 10 + [ATK]))
    assert v.stage1.ok and v.stage1.n == 5 and not v.stage1.infinite and v.stage1.limit_est == 9
    assert v.stage2.beat_win and not v.stage2.loop_win and v.stage2.kill and not v.stage2.ok
    assert v.stage2.attacks_after_loop == 1 and "殴り勝ち" in v.stage2.reason


def test_infinite_certificate_deck_out():
    cert = {"source": "certificate", "verified": True, "limit": "inf", "stocked": 26, "delta": {"deck:1": -1},
            "win_by": "opp_deck_out", "own_turn": 1}
    v = judge(GameResult(seed=0, first_player=0, kind="loop_deck_out", kill_turn=1, loops=[cert]), _eng([]))
    assert v.stage1.infinite and v.stage2.ok and v.stage2.via == "loop" and v.stage2.win_turn == 1


def test_self_deck_out_fails():
    v = judge(GameResult(seed=0, first_player=0, lost="deck_out", loops=[PAT]), _eng([]))
    assert v.stage1.ok and not v.stage2.ok and v.stage2.self_deck_out


def test_lock_recorded_as_route():
    res = GameResult(seed=0, first_player=0, kind="lock", kill_turn=2, lock={"limit": "inf"})
    v = judge(res, _eng([], opp_mana=0), lock_mode="active")
    assert v.stage2.via == "lock" and v.stage2.ok and v.stage2.lock["mode"] == "active" and v.stage2.lock["opp_mana_zero"]


def test_win_without_loop_in_win_turn_is_other():
    v = judge(GameResult(seed=0, first_player=0, kind="effect", kill_turn=4, loops=[PAT]), _eng([]))
    assert v.stage2.via == "other" and not v.stage2.ok and v.stage2.kill


@pytest.fixture(scope="module")
def rules():
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        return load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old


@pytest.mark.parametrize("name,turns", [("saga", 2), ("akashic", 1)])
def test_entries_pass_both_stages(rules, name, turns):
    ls = L.load(name)
    for sd in (0, 1):
        res, eng = play_game(rules, L.deck_of(ls), [], sd, max_turn=turns, budget=ls.source.get("budget", 200),
                             start=L.build(rules, ls, sd), lock_judge=lock_probe)
        v = judge(res, eng)
        assert v.stage1.ok and v.stage2.ok and v.stage2.via == "loop", v.reason
        assert v.stage1.infinite == (name == "akashic")


def test_knight_normal_game_has_no_loop(rules):
    deck = yaml.safe_load(open("data/decks/knight_dmc.yaml", encoding="utf-8"))["deck"]
    res, eng = play_game(rules, deck, ["T001"] * 40, 0, max_turn=4, budget=200, lock_judge=lock_probe)
    v = judge(res, eng)
    assert not v.stage1.ok and not v.stage2.ok


def test_mana_only_finite_repeat_is_not_a_loop():
    """マナを払って同じ札を使い直すだけの有限の繰り返し（差分が自分のマナの減りだけ）は段1に数えない（2026-11-14）。"""
    lp = {"source": "pattern", "verified": True, "kind": "finite", "laps": 3, "stocked": 3, "delta": {"untapped_mana:0": -1},
          "limit_est": 4, "own_turn": 2}
    v = judge(GameResult(seed=0, first_player=0, loops=[lp]), _eng([]))
    assert not v.stage1.ok and "払うだけ" in v.stage1.reason
