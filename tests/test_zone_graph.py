"""ゾーン変換グラフ（静的な解析）が、動的に検出したループと同じ差分を出すこと。"""
from dmsim import scenario as sc
from dmsim.loop import LoopDetector
from dmsim.zone_graph import find_cycles

from test_saga_loop import SAGA, saga_policy


def test_saga_is_a_single_card_cycle_with_the_same_delta_as_the_detector(rules):
    cyc = [c for c in find_cycles(rules, max_cards=1) if c.cards == [SAGA]]
    assert len(cyc) == 1 and cyc[0].conditional()
    static = cyc[0].delta()
    assert static == {"deck": -1, "graveyard": 1}

    eng = sc.build(rules, {"p0": {"hand": [SAGA, "T001", "T001", "T001", "T001", "T001"],
                                  "mana": ["dm01-080", "dm01-080", "dm01-027"],
                                  "graveyard": [SAGA, "T001", "T001", "T001"]},
                           "p1": {}, "deck_size": 40, "deck_left": [10, 40], "seed": 1})
    det = LoopDetector(me=0, period="in_turn", report_all=True)
    cert = None
    while cert is None:
        d = eng.advance()
        cert = det.observe(eng)
        if cert is None:
            eng.answer(saga_policy(eng, d))
    dynamic = {k.split(":")[0]: v for k, v in cert.delta.items()}
    assert dynamic == static


def test_no_cycle_for_cards_that_do_not_feed_each_other(rules):
    names = {c for cy in find_cycles(rules, max_cards=2) for c in cy.cards}
    assert "dm01-001" not in names           # グラン・ギューレ（ループと無関係）


def test_package_search_uses_cycle_cards_as_fixed_parts(rules):
    from dmsim.combo_search import package_search
    out = package_search(rules, ["T001", "dm01-001"], max_packages=1, slots=1, copies=2, games=1,
                         finalists=1, finalist_games=1, turns=1, budget=20)
    cards, res = out[0]
    assert cards and all(c in rules.cards for c in cards)
    assert all(all(x in c.deck for x in cards) for c in res)       # 部品はすべての構成に入っている


def test_dig_and_speed_metrics(rules):
    from dmsim.pool_metrics import dig, dig_total, speed
    assert dig(rules.cards["dm22ex1-025"]) >= 5            # イザナギテラス: 山札の上5枚
    assert speed(rules.cards["dm22ex1-025"]) == 4
    assert dig_total(rules, ["dm22ex1-025"] * 2) == 2 * dig(rules.cards["dm22ex1-025"])
