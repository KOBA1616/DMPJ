"""ループ記録は採った手順のものだけ（P2 タスク4）。候補は loop_candidates、サガ型の有限ループは source=pattern。"""
import pytest

from dmsim.eval import loop_entry as L
from dmsim.eval.lockcheck import lock_probe
from dmsim.search.game import play_game
from dmsim.search.pattern_loop import find


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


def _entry(rules, name, sd):
    ls = L.load(name)
    e = L.build(rules, ls, sd)
    return play_game(rules, L.deck_of(ls), [], sd, max_turn=1, budget=ls.source.get("budget", 200),
                     start=e, lock_judge=lock_probe)[0]


@pytest.mark.parametrize("sd", [0, 1])
def test_saga_entry_records_finite_loop_pattern_when_off(rules, sd, monkeypatch):
    import dmsim.search.turn as T
    monkeypatch.setattr(T, "DRAW_DISCARD", False)
    res = _entry(rules, "saga_v1", sd)
    lps = [lp for lp in res.loops if lp["source"] == "pattern"]
    assert res.kind == "effect" and lps and lps[0]["laps"] >= 3


@pytest.mark.parametrize("sd", [0, 1])
def test_saga_entry_records_finite_loop(rules, sd):
    res = _entry(rules, "saga_v1", sd)
    assert res.kind == "effect"
    # 引いて捨てる型の証明書（案 A）が入ってからは、探索中の証明書（wild の burn）として記録される。
    # 切った設定（draw_discard=False）では従来どおり事後検出（pattern）になる
    cert = [lp for lp in res.loops if lp["source"] == "certificate"]
    if cert:
        lp = cert[0]
        assert lp["kind"] == "burn" and lp["wild"] and lp["verified"] and lp["stocked"] >= 1
        assert lp["delta"].get("deck:0", 0) < 0
        return
    lps = [lp for lp in res.loops if lp["source"] == "pattern"]
    assert lps, res.loops
    lp = lps[0]
    assert lp["laps"] >= 3 and lp["infinite"] is False and lp["verified"]
    assert lp["delta"].get("deck:0", 0) < 0                     # 1周ごとに自分の山札が減る
    assert any("dm22ex2-021" in a for a in lp["anchor"])         # 錨は墓地の絶望神サガ


def test_akashic_entry_records_chosen_certificate(rules):
    res = _entry(rules, "akashic_v1", 0)
    assert res.kind == "loop_deck_out"
    assert [lp["source"] for lp in res.loops] == ["certificate"]
    assert res.loops[0]["win_by"] == "opp_deck_out"
    assert all(lp in res.loop_candidates for lp in res.loops)     # 採った線は候補の部分集合


def test_normal_knight_game_has_no_loop(rules):
    from dmsim.eval.measure import load_deck
    d = load_deck("data/decks/knight_dmc.yaml")
    for sd in range(2):
        res, _ = play_game(rules, d, d, sd, first_player=sd % 2, max_turn=6, budget=100, lock_judge=lock_probe)
        assert res.loops == [] and res.origin in (None, "combat")


def _ent(kind, keys):
    return {"p": 0, "kind": kind, "choice": [0], "keys": keys}


def test_plain_repeated_plays_are_not_loops():
    # 錨（墓地・場・マナの同じ札）が無い繰り返しは再生する前に弾く（start は使われない）
    entries = [x for i in range(8) for x in (_ent("main", ["play:x"]), _ent("choose_cards", [f"hand:c{i}:0"]))]
    assert find(None, entries, 0) == []
