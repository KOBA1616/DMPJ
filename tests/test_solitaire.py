"""1人回しAI とキル率測定ハーネス（dmsim.solitaire）。"""
from conftest import setup

from dmsim.play import make_record, replay_record
from dmsim.solitaire import lock_probe, measure, play_game, summarize


def test_in_turn_loop_is_found_by_search_and_stocked(rules):
    """探索中に T009+T010 のループを見つけ、ストックして相手の山札を削り切る（1ターン目でキル）。"""
    e = setup(rules, {"bz": ["T010"], "hand": ["T009"], "mana": ["T003"]})
    res, end = play_game(rules, None, None, 1, start=e, budget=50)
    assert res.error is None
    assert (res.kill_turn, res.kind) == (1, "loop_deck_out")
    assert res.loops[0]["win_by"] == "opp_deck_out" and res.loops[0]["delta"] == {"deck:1": -1, "graveyard:1": 1}
    assert end.s.result["winner"] == 0


def test_round_lock_counts_from_the_turn_it_is_set_up(rules):
    """手札の T021（毎ターン相手のマナを全部墓地へ）を1ターン目に出す → そのターンにロック確立。"""
    e = setup(rules, {"hand": ["T021"], "mana": ["T008"] * 6}, deck_size=40, deck_left=[30, 12])
    res, _ = play_game(rules, None, None, 1, start=e, budget=50)
    assert (res.kill_turn, res.kind) == (1, "lock")
    assert res.lock["delta"]["deck:1"] == -1 and res.lock["needed_rounds"] <= res.lock["limit"]


def test_lock_probe_rejects_non_locks_and_own_deck_out(rules):
    # 相手のマナが毎ターン増える → ロックではない
    e = setup(rules, {"bz": ["T001"]}, deck_size=40, deck_left=[30, 12])
    e.advance()
    assert lock_probe(e, 0) is None
    # 自分の山札が先に尽きる → ロックとして認めない（自分の山札切れ対策）
    e = setup(rules, {"bz": ["T021"]}, deck_size=40, deck_left=[5, 30])
    e.advance()
    assert lock_probe(e, 0) is None
    e = setup(rules, {"bz": ["T021"]}, deck_size=40, deck_left=[30, 12])
    e.advance()
    assert lock_probe(e, 0) is not None


def test_measure_is_reproducible_and_records_replay(rules):
    deck = ["T005"] * 20 + ["T002"] * 20
    opp = ["T001"] * 40
    a = measure(deck, opp, range(1, 4), rules=rules, max_turn=5, budget=60)
    b = measure(deck, opp, range(1, 4), rules=rules, max_turn=5, budget=60)
    assert [(r.seed, r.first_player, r.kill_turn, r.kind) for r in a] == \
           [(r.seed, r.first_player, r.kill_turn, r.kind) for r in b]
    assert all(r.error is None for r in a) and len(a) == 6     # 先攻・後攻の両方
    s = summarize(a, 5)
    assert s["kill_rate_by_turn"][5]["kills"] == sum(1 for r in a if r.kill_turn and r.kill_turn <= 5) > 0
    res, eng = play_game(rules, deck, opp, 2, max_turn=5, budget=60)
    rec = make_record(eng, [deck, opp], 2)
    assert replay_record(rules, rec).s.digest() == eng.s.digest()
