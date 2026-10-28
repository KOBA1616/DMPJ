"""1人回しAI とキル率測定ハーネス（dmsim.solitaire）。"""
from pathlib import Path

import pytest
from conftest import find_option, setup

from dmsim import load_rules
from dmsim.defs import card_yaml_files  # noqa: E402
from dmsim.defs import DATA
from dmsim.play import make_record, replay_record
from dmsim.solitaire import TurnSearch, Weights, lock_probe, measure, play_game, summarize


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


# ---- ドローを含むループ ------------------------------------------------------------------------

@pytest.fixture(scope="module")
def loop_rules():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "loop_cards.yaml"])


def test_loop_with_draw_is_detected_and_kills(loop_rules):
    """L001（引く＋相手の山札を1枚削る）を T010 で戻し続ける。引くたび手札の中身が変わっても同じループとして扱う。"""
    e = setup(loop_rules, {"bz": ["T010"], "hand": ["L001"], "mana": ["T003"]}, deck_left=[30, 12])
    res, end = play_game(loop_rules, None, None, 1, start=e, budget=50)
    assert res.error is None
    assert (res.kill_turn, res.kind, res.origin) == (1, "loop_deck_out", "loop")
    lp = res.loops[0]
    assert lp["win_by"] == "opp_deck_out" and lp["delta"]["hand:0"] == 1 and lp["delta"]["deck:0"] == -1
    assert end.s.result["winner"] == 0


def test_draw_loop_is_not_stocked_past_own_deck(loop_rules):
    """相手に効かない引くだけのループは、自分の山札を deck_keep 枚より減らさない範囲でストックする。"""
    e = setup(loop_rules, {"bz": ["T010"], "hand": ["L002"], "mana": ["T003"]}, deck_left=[20, 30])
    w = Weights()
    search = TurnSearch(0, budget=200, weights=w)
    e.advance()
    e.answer([find_option(e.s.waiting, "pass")])      # マナチャージはしない
    end, st = search.run(e)
    engine = [lp for lp in st.loops if lp["kind"] == "engine"]
    assert engine and engine[0]["delta"]["hand:0"] == 1
    assert len(end.zlist("deck", 0)) >= w.deck_keep


def test_combat_win_is_not_counted_as_loop(rules):
    deck, opp = ["T005"] * 20 + ["T002"] * 20, ["T001"] * 40
    rs = measure(deck, opp, range(1, 4), rules=rules, max_turn=5, budget=60)
    s = summarize(rs, 5)
    assert "loop" not in s["origins"] and s["loop_kill_rate_by_turn"][5] == 0


# ---- 相手の妨害モデル --------------------------------------------------------------------------

def test_opp_none_matches_default(rules):
    from dmsim.opponent import PRESETS
    deck, opp = ["T005"] * 20 + ["T002"] * 20, ["T001"] * 40
    a = measure(deck, opp, range(1, 4), rules=rules, max_turn=5, budget=60)
    b = measure(deck, opp, range(1, 4), rules=rules, max_turn=5, budget=60, opp=PRESETS["none"])
    assert [(r.kill_turn, r.kind) for r in a] == [(r.kill_turn, r.kind) for r in b]


def test_opp_model_setup_and_blocker_policy(rules):
    from dmsim.opponent import OppModel
    deck, opp = ["T005"] * 40, ["T001"] * 20 + ["T004"] * 20
    m = OppModel(shields=3, bz=("T004",), block=True, play="blockers")
    res, eng = play_game(rules, deck, opp, 1, max_turn=1, budget=20, opp=m)
    assert res.error is None
    assert len(eng.s.zones["shield"][1]) == 3
    assert any(eng.s.cards[c].defn == "T004" for c in eng.zlist("bz", 1))


def test_opp_blockers_lower_kill_rate(rules):
    from dmsim.opponent import PRESETS
    deck, opp = ["T005"] * 20 + ["T002"] * 20, ["T001"] * 20 + ["T004"] * 20
    base = summarize(measure(deck, opp, range(1, 9), rules=rules, max_turn=5, budget=60), 5)
    blk = summarize(measure(deck, opp, range(1, 9), rules=rules, max_turn=5, budget=60, opp=PRESETS["blockers"]), 5)
    assert not blk["errors"]
    assert blk["kill_rate_by_turn"][5]["kills"] <= base["kill_rate_by_turn"][5]["kills"]
