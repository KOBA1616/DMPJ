"""局面評価 V（勝敗を使わない）の基本。"""
from conftest import setup
from dmsim.discovery import advantage as adv


def test_weights_load_and_value_is_self_minus_opp(rules):
    w = adv.load_weights()
    e = setup(rules, {"hand": ["T001"] * 3}, {"hand": ["T001"]})
    v = adv.board_value(e, 0, w)
    me, opp = adv.resource_vector(e, 0), adv.resource_vector(e, 1)
    assert me["hand"] == 3 and opp["hand"] == 1
    assert abs(v - adv.value(me, opp, w)) < 1e-9
    assert adv.board_value(e, 1, w) < v           # 手札が多い側の方が高い


def test_value_fn_can_replace_the_turn_search_leaf_evaluation(rules):
    # 局面評価を葉の評価に使っても、自分の1ターンを回して資源ベクトルを返す
    v, vec = adv.turn_value(rules, {"p0": {"hand": ["T001"] * 2}, "p1": {}})
    assert set(vec) == set(adv.RES) and isinstance(v, float)


def test_search_does_not_treat_a_nonrepeatable_chain_as_a_loop():
    """骨格が戻るだけの1回きりの連鎖（騎士の効果）を、検証できないままループ扱いして枝を捨てない。"""
    import pathlib
    import tempfile
    import test_dmc_knight as t
    rules = t._small_rules(pathlib.Path(tempfile.mkdtemp()))
    spec = {"p0": {"mana": [t.D] * 3, "hand": [t.K], "graveyard": [t.D]}, "p1": {"bz": ["T001"]}, "seed": 1}
    v, vec = adv.turn_value(rules, spec)
    assert vec["board"] == 2 and vec["shield"] == 6      # 騎士の効果を使い、DMC が墓地から戻る


def test_scan_pair_finds_where_knight_and_dmc_work_together_and_ignores_a_control():
    import pathlib
    import tempfile
    import test_dmc_knight as t
    rules = t._small_rules(pathlib.Path(tempfile.mkdtemp()))
    kw = dict(base={"mana": [t.D] * 3}, opp={"bz": ["T001"]}, places=("hand", "graveyard", "mana"), seeds=(1,))
    got = {(r["place_a"], r["place_b"]): r["S"] for r in adv.scan_pair(rules, t.K, t.D, **kw)}
    assert got[("hand", "hand")] > 3 and got[("hand", "graveyard")] > 3     # 手札の騎士＋手札/墓地の DMC
    assert got[("hand", "mana")] < 0.5                                       # マナにある DMC は組にならない
    ctl = adv.scan_pair(rules, t.K, "T001", **kw)
    assert all(abs(r["S"]) < 0.5 for r in ctl)                               # 無関係な組は相乗効果がない
