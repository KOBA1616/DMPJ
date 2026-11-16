"""第3段・共通基盤その1: selector の `exclude`（参照除外。設計 design-full-bandC1.md U35）。

- selector に「参照中の1体（または束縛した選択結果）を除く」指定が無く、「〜以外の
  クリーチャーをすべて」の型が書けなかった（gap selector_exclude 5件／exclude_ref 3件）。
- 変更: defs.py の SELECTOR_KEYS に exclude を追加し、selector 検証で再帰検証する。
  selectors.py の candidates は、ゾーン経路の候補計算の最後（filter 適用後）に
  exclude の候補（各要素を candidates で評価した和集合）を引く。ref／under_of 等の
  特殊経路には適用しない（設計 §4 どおり）。
- proto: T225（choose → それ以外をすべてタップ。dmex14-s04 型）／
  T226（リスト形で2体を除外。2回目の choose 自身にも exclude が効く）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def _tapped(e, p, defn):
    # バトルゾーンは共有ゾーンなので、コントローラーで絞る
    return [e.s.cards[c].tapped for c in e.zlist("bz", p)
            if e.s.cards[c].defn == defn and e.s.cards[c].controller == p]


def _cast(e, defn, picks):
    """手札の呪文 defn を唱える。picks は choose_cards で選ぶキー（先頭一致の順）。
    解決が終わって次の main または attack の判断まで進める。"""
    picks = list(picks)
    for _ in range(200):
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge":
            e.answer([keys.index("pass")])
        elif d["kind"] == "main":
            if f"play:{defn}" in keys:
                e.answer([keys.index(f"play:{defn}")])
            else:
                return   # 解決後、次の main に戻った
        elif d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_cards":
            want = picks.pop(0)
            assert want in keys, f"{want} not in {keys}"
            e.answer([keys.index(want)])
        elif d["kind"] == "attack":
            return
        else:
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("cast did not resolve")


def test_proto_parse(rules):
    """T225／T226 が parse でき、exclude の検証（再帰・型）が効く。"""
    for cid in ("T225", "T226"):
        parse_card(_proto_card(cid), TABLES)
    bad = _proto_card("T225")
    bad["spell"][1]["select"]["exclude"] = 5
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad2 = _proto_card("T225")
    bad2["spell"][1]["select"]["exclude"] = {"ref": "picked", "bogus": 1}
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)


def test_exclude_keeps_chosen_one(rules):
    """設計 §6(1): 選んだ1体だけが残り、それ以外のクリーチャー（相手の分も含む）がすべてタップされる。"""
    e = setup(rules, {"bz": ["T001", "T004", "T017"], "hand": ["T225"], "mana": ["T003"] * 3},
              {"bz": ["T001"]})
    _cast(e, "T225", ["bz:T004:0"])
    assert _tapped(e, 0, "T004") == [False]          # 選んだ1体はタップされない
    assert _tapped(e, 0, "T001") == [True]
    assert _tapped(e, 0, "T017") == [True]
    assert _tapped(e, 1, "T001") == [True]           # owner: any なので相手のクリーチャーも対象


def test_exclude_empty_ref_targets_all(rules):
    """設計 §6(2): exclude の参照が空（先行選択が空振り）の時は、全員が対象になる。
    candidates の水準で確認する（タップ結果は相手ターン開始のアンタップで観測できなくなるため）。"""
    e = setup(rules, {}, {"bz": ["T001", "T004"]})
    sel = {"zone": "bz", "owner": "any", "filter": {"types": ["creature"]}, "count": "all",
           "exclude": {"ref": "picked"}}
    env = {"you": 0, "vars": {"picked": []}}   # choose が空振りした状態（空リストが束縛されている）
    assert sorted(e.s.cards[c].defn for c in e.candidates(sel, env)) == ["T001", "T004"]
    env_missing = {"you": 0, "vars": {}}       # 変数自体が無い場合も同じ
    assert sorted(e.s.cards[c].defn for c in e.candidates(sel, env_missing)) == ["T001", "T004"]
    ref = e.s.ref(next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T001"))
    env_bound = {"you": 0, "vars": {"picked": [ref]}}
    assert [e.s.cards[c].defn for c in e.candidates(sel, env_bound)] == ["T004"]


def test_exclude_list_form(rules):
    """設計 §6(3): リスト形で2体を除ける。2回目の choose の候補からも1体目が外れている。"""
    e = setup(rules, {"bz": ["T001", "T004", "T017", "T005"], "hand": ["T226"], "mana": ["T003"] * 4},
              {})
    _cast(e, "T226", ["bz:T001:0", "bz:T004:0"])
    assert _tapped(e, 0, "T001") == [False]
    assert _tapped(e, 0, "T004") == [False]
    assert _tapped(e, 0, "T017") == [True]
    assert _tapped(e, 0, "T005") == [True]
