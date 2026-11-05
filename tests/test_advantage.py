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


def test_combo_report_gain_matches_card_text():
    """墓地の DMC を、騎士の盾置きで戻す。基準線（騎士のみ）に対する増分は 手札+2・バトルゾーン+1・山札−2。"""
    import pathlib
    import tempfile
    import test_dmc_knight as t
    rules = t._small_rules(pathlib.Path(tempfile.mkdtemp()))
    r = adv.combo_report(rules, {"hand": [t.K]}, {"graveyard": [t.D]}, {"mana": [t.D] * 3}, opp={"bz": ["T001"]}, seeds=(1,))
    assert r["is_combo"] and r["gain_over_a"]["hand"] == 2 and r["gain_over_a"]["board"] == 1 and r["gain_over_a"]["deck"] == -2


def test_causal_link_knight_causes_dmc_trigger_and_control_has_none():
    import pathlib
    import tempfile
    import test_dmc_knight as t
    rules = t._small_rules(pathlib.Path(tempfile.mkdtemp()))
    spec = {"p0": {"mana": [t.D] * 3, "hand": [t.K], "graveyard": [t.D]}, "p1": {"bz": ["T001"]}, "seed": 1}
    _, _, links, _ = adv.traced_turn(rules, spec)
    assert (t.K, t.D) in links                       # 騎士の盾置き → DMC の墓地誘発
    r = adv.combo_report(rules, {"hand": [t.K]}, {"hand": ["T001"]}, {"mana": [t.D] * 3}, opp={"bz": ["T001"]}, seeds=(1,))
    assert not r["is_combo"] and r["causal_links"] == []


def test_detect_conversion_flags_a_solo_disadvantage_that_pays_off_in_a_pair():
    # A 単体は「なし」より低い（デメリット）が、B と組むと B 単体より高い → A がデメリット変換
    assert adv.detect_conversion({"none": 1.0, "a": -1.0, "b": 2.0, "ab": 6.0}) == ["a"]
    # 騎士のように単体でも得なカードは、デメリット変換ではない
    assert adv.detect_conversion({"none": 0.5, "a": 5.5, "b": 0.7, "ab": 10.65}) == []
    # 組にしても回収されないデメリットは対象外
    assert adv.detect_conversion({"none": 1.0, "a": -1.0, "b": 2.0, "ab": 1.5}) == []


def test_scan_pair_report_separates_working_and_failing_places():
    import pathlib
    import tempfile
    import test_dmc_knight as t
    rules = t._small_rules(pathlib.Path(tempfile.mkdtemp()))
    x = adv.scan_pair_report(rules, t.K, t.D, base={"mana": [t.D] * 3}, opp={"bz": ["T001"]}, places=("hand", "graveyard", "mana"), seeds=(1,))
    assert {(w["place_a"], w["place_b"]) for w in x["works"]} == {("hand", "hand"), ("hand", "graveyard")}
    assert len(x["fails"]) == 7 and all(f["S"] <= 1e-9 or not f["causal_links"] for f in x["fails"])


def test_audit_catches_a_duplicated_trigger_and_passes_the_fixed_card():
    import copy
    import pathlib
    import tempfile
    import test_dmc_knight as t
    from dmsim.discovery import audit
    rules = t._small_rules(pathlib.Path(tempfile.mkdtemp()))
    assert audit.audit_card(rules, t.D)["ok"] is True                 # 原文どおり 2枚引く
    cd = rules.cards[t.D]
    cd.abilities.append(copy.deepcopy(next(a for a in cd.abilities if a.get("effect") == [{"op": "draw", "count": 2}])))   # 二重登録を再現
    bad = audit.audit_card(rules, t.D)
    assert bad["ok"] is False and bad["measured"]["draws"] == 4
    assert audit.predict_cip("このクリーチャーが出た時、カードを２枚引く。") == {"draws": 2, "discards": 0}
    assert audit.predict_cip("このクリーチャーが出た時、カードを２枚引いてもよい。") is None   # 条件つきは予測しない
