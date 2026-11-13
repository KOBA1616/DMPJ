"""語彙パイロット第189弾（2026-11-12）の検証。

summon_time_cost の残り（第6弾の opt_reduce では表せなかった3形）。
- do.selects: 複数の選択肢（手札・クリーチャー・タマシード・シールドを最大1つずつ等）。
  燃料は全項目の合算で、per の軽減はその合計枚数 × amount。
- do.strigger_off: 燃料を手札へ動かす時、そのカードの S・トリガーを使えない印を付ける。
- summon_fuel: 召喚時の支払い行動で選んだカードを [cid, gen] でカードに刻む（ゾーン移動で消える。
  summon_tapped と同じ作法でイベントに載せて出し直す）。セレクタ {ref: fuel} で参照でき、
  「このクリーチャーが出た時、選んだシールドを手札に加える」を出た時の誘発で書ける。
"""
from pathlib import Path

import pytest
import yaml
from conftest import answer, setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()
PROTOS = ("T458", "T459", "T460")


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def drive(e, plan, limit=80):
    """plan: {decision_kind: [[answer keys or indices], ...]} 同じ種類の判断が続く場合はキューで順に使う。"""
    plan = {k: list(v) for k, v in plan.items()}
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        queue = plan.get(d["kind"])
        if not queue:
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
            continue
        want = queue.pop(0)
        ans = []
        for w in want:
            ans.append(keys.index(w) if isinstance(w, str) else w)
        e.answer(sorted(set(ans)))
        if not any(plan.values()):
            plan.clear()
        if not plan:
            # 残りは pass で流して召喚の解決まで進める
            for _ in range(limit):
                d = e.advance()
                if d is None or d["kind"] in ("main", "attack"):
                    return
                keys = [o["key"] for o in d["options"]]
                e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
            return
    raise AssertionError("drive did not finish")


def _tapped_mana(e, player=0):
    return [c for c in e.zlist("mana", player) if e.s.cards[c].tapped]


def _by_defn(e, zone, player, defn):
    return [c for c in e.zlist(zone, player) if e.s.cards[c].defn == defn]


def test_parse_protos():
    for cid in PROTOS:
        parse_card(_proto_card(cid), TABLES)


def test_bad_do_forms_rejected():
    base = _proto_card("T458")
    both = yaml.safe_load(yaml.safe_dump(base))
    both["abilities"][0]["mod"]["opt_reduce"]["do"]["select"] = {"zone": "hand", "owner": "you"}
    with pytest.raises(DefError):
        parse_card(both, TABLES)
    neither = yaml.safe_load(yaml.safe_dump(base))
    del neither["abilities"][0]["mod"]["opt_reduce"]["do"]["selects"]
    with pytest.raises(DefError):
        parse_card(neither, TABLES)
    bad_flag = yaml.safe_load(yaml.safe_dump(_proto_card("T459")))
    bad_flag["abilities"][0]["mod"]["opt_reduce"]["do"]["strigger_off"] = "yes"
    with pytest.raises(DefError):
        parse_card(bad_flag, TABLES)


def test_multi_select_four_fuel(rules):
    """手札・クリーチャー・タマシード・シールドを1つずつ墓地へ置き、7→3で召喚できる。
    T001 を手札に残しておくと、召喚後のメイン決定で止まってタップ数が見える（第187弾の教訓）。"""
    e = setup(rules, {"hand": ["T458", "T002", "T001"], "mana": ["T460", "T460", "T460", "T001", "T001"],
                      "bz": ["T001", "T189"], "shield": ["T001"]}, {})
    answer(e, "charge", "pass")
    drive(e, {"main": [["play:T458"]],
              "choose_cards": [["reduce"], [0], [0], [0], [0]],
              "pay_mana": [["mana:T460,T460,T460"]]})
    assert _by_defn(e, "bz", 0, "T458")
    assert _by_defn(e, "graveyard", 0, "T002")
    assert _by_defn(e, "graveyard", 0, "T001")
    assert _by_defn(e, "graveyard", 0, "T189")
    assert len(_tapped_mana(e)) == 3


def test_multi_select_partial_fuel(rules):
    """手札とシールドだけ選ぶと 7→5。選ばなかったクリーチャーとタマシードは場に残る。"""
    e = setup(rules, {"hand": ["T458", "T002"], "mana": ["T460"] * 5,
                      "bz": ["T001", "T189"], "shield": ["T001"]}, {})
    answer(e, "charge", "pass")
    drive(e, {"main": [["play:T458"]],
              "choose_cards": [["reduce"], [0], [], [], [0]]})
    assert _by_defn(e, "bz", 0, "T458")
    assert _by_defn(e, "graveyard", 0, "T002")
    assert _by_defn(e, "bz", 0, "T001")
    assert _by_defn(e, "bz", 0, "T189")
    assert len(_by_defn(e, "shield", 0, "T001")) == 0
    assert len(_tapped_mana(e)) == 5


def test_multi_select_no_fuel(rules):
    """手札の燃料を辞退すると軽減なしで 7 コストのまま召喚できる（壊れない）。"""
    e = setup(rules, {"hand": ["T458", "T001"], "mana": ["T460"] * 7 + ["T001"] * 2, "shield": []}, {})
    answer(e, "charge", "pass")
    drive(e, {"main": [["play:T458"]], "choose_cards": [["reduce"], []],
              "pay_mana": [["mana:T460,T460,T460,T460,T460,T460,T460"]]})
    assert _by_defn(e, "bz", 0, "T458")
    assert len(_tapped_mana(e)) == 7


def test_no_fuel_not_playable_with_six_mana(rules):
    """燃料が無ければ見積もりは 7 のまま。マナ6枚では出せない（_opt_reduced の見積もり確認）。"""
    e = setup(rules, {"hand": ["T458"], "mana": ["T460"] * 6, "shield": []}, {})
    cid = e.zlist("hand", 0)[0]
    assert e._can_play_face(cid, 0, None) is False
    e = setup(rules, {"hand": ["T458"], "mana": ["T460"] * 7, "shield": []}, {})
    cid = e.zlist("hand", 0)[0]
    assert e._can_play_face(cid, 0, None) is True


def test_shield_to_hand_strigger_off(rules):
    """シールドを手札に加えて 6→3。加わった S・トリガー呪文には使えない印が付く。"""
    e = setup(rules, {"hand": ["T459", "T001"], "mana": ["T460", "T460", "T460", "T001", "T001"],
                      "shield": ["T006"]}, {})
    answer(e, "charge", "pass")
    # シールド1枚だけが候補で min=max=1 のため燃料選択は自動確定し、決定は出ない。
    drive(e, {"main": [["play:T459"]], "choose_cards": [["reduce"]],
              "pay_mana": [["mana:T460,T460,T460"]]})
    assert _by_defn(e, "bz", 0, "T459")
    moved = _by_defn(e, "hand", 0, "T006")
    assert len(moved) == 1
    assert e.s.cards[moved[0]].strigger_off is True
    assert len(_tapped_mana(e)) == 3


def test_fuel_to_hand_at_cip(rules):
    """シールド2つを選び 5→3。出た時に選んだ2枚が手札へ加わり、S・トリガーは使えない。"""
    e = setup(rules, {"hand": ["T460", "T001"], "mana": ["T460", "T460", "T460", "T001", "T001"],
                      "shield": ["T006", "T003"]}, {})
    answer(e, "charge", "pass")
    drive(e, {"main": [["play:T460"]], "choose_cards": [["reduce"], [0, 1]],
              "pay_mana": [["mana:T460,T460,T460"]]})
    assert _by_defn(e, "bz", 0, "T460")
    for defn in ("T006", "T003"):
        moved = _by_defn(e, "hand", 0, defn)
        assert len(moved) == 1, defn
        assert e.s.cards[moved[0]].strigger_off is True, defn
    assert len(_by_defn(e, "shield", 0, "T006")) == 0
    assert len(_tapped_mana(e)) == 3


def test_fuel_to_hand_one_shield(rules):
    """シールド1つだけ選ぶと 5→4。選ばなかったシールドは残る。
    シールド同士は選択肢のキーで区別できないため、同名シールド2枚で試験する。"""
    e = setup(rules, {"hand": ["T460", "T001"], "mana": ["T460"] * 4 + ["T001"] * 2,
                      "shield": ["T006", "T006"]}, {})
    answer(e, "charge", "pass")
    drive(e, {"main": [["play:T460"]], "choose_cards": [["reduce"], [0]],
              "pay_mana": [["mana:T460,T460,T460,T460"]]})
    assert _by_defn(e, "bz", 0, "T460")
    assert len(_by_defn(e, "hand", 0, "T006")) == 1
    assert len(_by_defn(e, "shield", 0, "T006")) == 1
    assert len(_tapped_mana(e)) == 4


def test_fuel_to_hand_no_shield(rules):
    """シールドを選ばないと 5 コストのまま。出た時の誘発は空振りして何も起きない。"""
    e = setup(rules, {"hand": ["T460", "T001"], "mana": ["T460"] * 5 + ["T001"] * 2,
                      "shield": ["T006", "T003"]}, {})
    answer(e, "charge", "pass")
    drive(e, {"main": [["play:T460"]], "choose_cards": [["reduce"], []],
              "pay_mana": [["mana:T460,T460,T460,T460,T460"]]})
    assert _by_defn(e, "bz", 0, "T460")
    assert len(_by_defn(e, "shield", 0, "T006")) == 1
    assert len(_by_defn(e, "shield", 0, "T003")) == 1
    assert len(_tapped_mana(e)) == 5


def test_summon_fuel_recorded(rules):
    """召喚時燃料は出たクリーチャーに刻まれる（ref: fuel の参照元）。"""
    e = setup(rules, {"hand": ["T460"], "mana": ["T460", "T460", "T460"],
                      "shield": ["T006", "T003"]}, {})
    answer(e, "charge", "pass")
    drive(e, {"main": [["play:T460"]], "choose_cards": [["reduce"], [0, 1]],
              "pay_mana": [["mana:T460,T460,T460"]]})
    top = _by_defn(e, "bz", 0, "T460")
    assert len(top) == 1
    assert len(e.s.cards[top[0]].summon_fuel) == 2
