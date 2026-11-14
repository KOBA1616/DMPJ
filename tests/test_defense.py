"""相手のターン中の自分の防御（search.defense、2026-11-14）。"""
from dmsim.search import defense
from dmsim.search.game import play_game


def test_wrap_disabled_returns_same_policy():
    was = defense.enabled()
    defense.set_enabled(False)
    f = lambda e, d: [0]
    try:
        assert defense.wrap(f, 0) is f
    finally:
        defense.set_enabled(was)


def _blocks(eng):
    return sum(1 for ent in eng.log if ent["p"] == 0 and ent["kind"] == "block" and ent["keys"][0] != "no_block")


def test_blocks_against_attackers_when_enabled(rules):
    from dmsim.search.opponent import OppModel
    deck, opp = ["T004"] * 40, ["T005"] * 40          # 自分: ブロッカー（3000）、相手: SA・W・ブレイカー（3000）
    m = OppModel("aggro_test", play="all", attack="all")
    seen, lost = {}, {}
    was = defense.enabled()
    try:
        for on in (False, True):
            defense.set_enabled(on)
            res, eng = play_game(rules, deck, opp, 3, max_turn=5, budget=20, opp=m, lock_rounds=0)
            assert res.error is None
            seen[on], lost[on] = _blocks(eng), res.lost
    finally:
        defense.set_enabled(was)
    assert seen[False] == 0 and seen[True] >= 1
