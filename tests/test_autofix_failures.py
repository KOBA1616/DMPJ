from dmsim.autofix.failures import classify_games, propose_from_failures, summarize
from dmsim.autofix.loop import Knobs


M = {"kill": [3, None, None, None, 6, None], "cards": [2, None, 1, 1, 1, 2], "board": [2, 3, None, 2, 2, 3],
     "prep": [1, 1, 1, 0, 1, 1]}


def test_classify():
    assert classify_games(M) == ["ok", "cards_miss", "board_miss", "prep_unused", "late_kill", "finish_miss"]


def test_summary_and_proposals_ordered_and_deck_only_for_cards():
    s = summarize(M)
    assert abs(s["ok_rate"] - 1 / 6) < 1e-9 and s["seeds"]["cards_miss"] == [1]
    ps = propose_from_failures(M, Knobs(), min_share=0.1)
    cards = [p for p in ps if p["class"] == "cards_miss"]
    assert cards and cards[0]["knobs"] is None and cards[0]["deck_hint"]
    assert any(p["class"] == "prep_unused" and p["knobs"].prep_bonus > 0 for p in ps)
    shares = [p["share"] for p in ps]
    assert shares == sorted(shares, reverse=True)


def test_no_failures_no_proposals():
    assert propose_from_failures({"kill": [2, 3]}, Knobs()) == []
