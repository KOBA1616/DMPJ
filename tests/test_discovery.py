"""dmsim.discovery: LoopSpec のデータ表現と、最小初期盤面の縮約（介入による特定）。"""
from pathlib import Path

import pytest
import yaml

from dmsim.eval import shrink as sh
from dmsim.base.loopspec import LoopSpec, Pred, hit_prob_within, reroll_success_prob

SAGA_SETUP = Path(__file__).parent / "saga_loop_first_setup.yaml"
SAGA, DRAGE, KODAMA = "dm22ex2-021", "dm22ex1-007", "dmex10-020"


def test_loopspec_json_roundtrip_and_validation():
    s = LoopSpec("exchange", "reroll", [Pred(0, {"name": SAGA}, 1, ">=", zones=("graveyard", "hand"))],
                 {"deck:0": -1}, goal=[Pred(0, {"types": ["creature"]}, 2, ">=", "graveyard")])
    assert LoopSpec.from_json(s.to_json()) == s
    with pytest.raises(ValueError):
        LoopSpec("x", "reroll", [])                                   # reroll には停止条件が要る
    with pytest.raises(ValueError):
        Pred(0, {"name": SAGA}, 1, ">=")                              # zone も zones も無い
    with pytest.raises(ValueError):
        Pred(0, {"name": SAGA}, 1, ">=", "hand", ("hand", "mana"))    # 両方は不可


def test_reroll_success_probability_is_hypergeometric():
    assert hit_prob_within(10, 1, 5) == pytest.approx(0.5)
    assert hit_prob_within(10, 0, 5) == 0.0 and hit_prob_within(10, 6, 5) == 1.0
    s = LoopSpec("x", "reroll", [], goal=[Pred(0, {"name": "a"}, 1, ">=", "hand")], deck_floor=1)
    assert reroll_success_prob(s, deck_n=11, hits=1) == pytest.approx(10 / 11)   # 山札の下限1枚を残すので10枚まで見られる
    assert reroll_success_prob(s, deck_n=11, hits=2) == 1.0


@pytest.mark.slow
def test_shrink_saga_board_to_one_minimal_board(rules):
    """サガの盤面を縮約すると、どの1枚を外してもループが成立しない最小の盤面になる（決定的）。"""
    spec = yaml.safe_load(SAGA_SETUP.read_text(encoding="utf-8"))
    found = sh.lf.discover_loops(sh.sc.build(rules, spec), 0, 1500)
    delta = next(f.cert.delta for f in found if f.verified)
    test = sh.loop_test(rules, 0, 1500, delta)
    r = sh.shrink(spec, test)
    names = sorted(n for _, _, _, n in sh.entries(r.spec))
    assert DRAGE not in names and KODAMA not in names     # 勝つための出口のカードは、ループの入口には要らない
    assert names.count(SAGA) == 2
    for pk, z, i, n in sh.entries(r.spec):                             # 1-極小: どれを外しても成立しない
        assert not test(sh.without(r.spec, pk, z, i))
    again = sh.shrink(spec, sh.loop_test(rules, 0, 1500, delta))
    assert again.spec == r.spec                                       # 同じ入力から同じ結果
    ls = sh.to_loopspec(rules, "saga", r, delta)
    assert ls.delta == delta and sum(p.n for p in ls.minimal) == len(sh.entries(r.spec))
    assert LoopSpec.from_json(ls.to_json()) == ls


def test_zone_alternatives_show_where_the_card_may_be(rules):
    """残ったカードが別のゾーンでも成立するか。サガは場にいても成立する。"""
    spec = {"p0": {"hand": [SAGA, DRAGE, KODAMA], "graveyard": [SAGA]}, "p1": {}, "deck_size": 40, "deck_left": [20, 40]}
    test = sh.loop_test(rules, 0, 1500, {"deck:0": -1, "graveyard:0": 1})
    alts = sh.zone_alternatives(spec, test, zones=("bz", "hand"))
    assert "bz" in alts[("p0", "graveyard", 0)]


def test_robust_shrink_does_not_let_a_creature_filler_hide_the_graveyard_requirement(rules):
    """filler がクリーチャーだと、引いて捨てるだけで墓地にクリーチャーが増え、必要な条件が隠れる。
    非クリーチャーの filler でも成立する最小盤面を採ると、墓地のクリーチャーの条件が現れる。"""
    spec = yaml.safe_load(SAGA_SETUP.read_text(encoding="utf-8"))
    spec["p0"]["hand"] = [c for c in spec["p0"]["hand"] if c != "T001"]   # 手札の試験用ダミー（クリーチャー）は使わない
    delta = {"deck:0": -1, "graveyard:0": 1}
    test = sh.loop_test(rules, 0, 1500, delta)
    r = sh.robust_shrink(spec, test, ["T001", "T013"])      # T001 はクリーチャー、T013 は呪文
    assert r.holds_for_all
    only_creature = sorted(n for _, _, _, n in sh.entries(r.per_filler["T001"]))
    assert DRAGE not in only_creature and KODAMA not in only_creature
    robust = sh.entries(r.spec)
    grave = [n for pk, z, _, n in robust if z == "graveyard"]
    assert len([n for n in grave if "creature" in rules.cards[n].types]) >= 2   # サガ以外にも墓地のクリーチャーが要る
    assert len(robust) > len(only_creature)


@pytest.mark.slow
def test_entrance_and_exit_are_separated(rules):
    """入口（ループが回る）にはドラゲリオンもコダマダンスも要らない。出口（勝利）に追加で要る。"""
    spec = yaml.safe_load(SAGA_SETUP.read_text(encoding="utf-8"))
    spec["p0"]["hand"] = [c for c in spec["p0"]["hand"] if c != "T001"]
    d = {"deck:0": -1, "graveyard:0": 1}
    r = sh.split_entrance_exit(spec, sh.loop_test(rules, 0, 1500, d), sh.win_test(rules, 0, 1500, 1500, d), ["T001", "T013"])
    assert r.wins
    ent = sorted(n for _, _, _, n in sh.entries(r.entrance))
    assert DRAGE not in ent and KODAMA not in ent
    assert {n for _, _, n in r.extra} >= {DRAGE, KODAMA}
    assert any(z == "graveyard" for _, z, _ in r.extra)           # 蘇生するシャコガイルは墓地に要る


def test_entrance_needs_no_mana_when_saga_waits_on_the_field(rules):
    """場で待機中のサガ、墓地のサガ、墓地のクリーチャー2枚があれば、マナなしでも回る（koba の定義）。"""
    spec = yaml.safe_load(SAGA_SETUP.read_text(encoding="utf-8"))
    spec["p0"]["hand"] = [c for c in spec["p0"]["hand"] if c != "T001"]
    test = sh.loop_test(rules, 0, 1500, {"deck:0": -1, "graveyard:0": 1})
    r = sh.robust_shrink(spec, test, ["T001", "T013"])
    zones = sorted(z for _, z, _, _ in sh.entries(r.spec))
    assert zones == ["bz", "graveyard", "graveyard", "graveyard"]
    assert [n for _, z, _, n in sh.entries(r.spec) if z == "bz"] == [SAGA]


def test_route_probability_matches_brute_force():
    """文明が揃う確率は、包含と排除の結果が全列挙と一致する。経路は LoopSpec の JSON に往復できる。"""
    from itertools import combinations

    from dmsim.base.loopspec import Route, all_civs_prob, route_prob
    w, d, f = frozenset({"water"}), frozenset({"darkness"}), frozenset({"fire"})
    deck = [w, w, d, f, f, frozenset({"water", "darkness"})]
    need = ("water", "darkness")
    combos = list(combinations(range(len(deck)), 3))
    ok = sum(1 for c in combos if all(any(n in deck[i] for i in c) for n in need))
    assert all_civs_prob(deck, need, 3) == pytest.approx(ok / len(combos))
    r = Route("cast", {"name": SAGA}, "hand", 3, need)
    assert 0.0 < route_prob(r, deck, 1, 4) < 1.0
    s = LoopSpec("x", "deterministic", [Pred(0, {"name": SAGA}, 1, ">=", "bz")], routes=[r])
    assert LoopSpec.from_json(s.to_json()) == s


@pytest.mark.slow
def test_full_loopspec_separates_entrance_exit_and_route(rules):
    spec = yaml.safe_load(SAGA_SETUP.read_text(encoding="utf-8"))
    spec["p0"]["hand"] = [c for c in spec["p0"]["hand"] if c != "T001"]
    d = {"deck:0": -1, "graveyard:0": 1}
    ee = sh.split_entrance_exit(spec, sh.loop_test(rules, 0, 1500, d), sh.win_test(rules, 0, 1500, 1500, d), ["T001", "T013"])
    ls = sh.full_loopspec(rules, "saga", ee, d)
    assert LoopSpec.from_json(ls.to_json()) == ls
    assert not any(p.match.get("name") in (DRAGE, KODAMA) for p in ls.minimal)       # 入口に出口のカードは無い
    assert {p.match["name"] for p in ls.goal} >= {DRAGE, KODAMA}                     # 出口に追加で要る
    r = next(r for r in ls.routes if r.card["name"] == SAGA)
    assert r.cost == 3 and set(r.civs) == {"water", "darkness"}                      # 手札から出す経路
