"""colorless フィルタ修正（2026-11-17）: 無色カードは civs: [zero] で登録されるため、
filter {colorless: true} は civs==[] だけでなく civs==[zero] にも一致しなければならない。

第66弾は colorless を「civs が空」と定義したが、実データの無色カードは [zero] で
登録されており（116件以上）、ゴッドリンク勢やピクシー・ライフ等の対象選択が
実カード相手では永遠に不発だった。Python（selectors.py）と Rust（engine.rs）の
両エンジンで一致条件を「空 または [zero]」に統一した。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

rules = load_rules()


def test_zero_civ_matches_colorless():
    e = build(rules, {"p0": {"bz": ["dm24bd2-016", "T001", "T008"]}, "p1": {},
                      "filler": "T002"})
    zero = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "dm24bd2-016")
    light = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T001")
    multi = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T008")
    # [zero] は無色
    assert e.filter_match(zero, {"colorless": True})
    assert not e.filter_match(zero, {"colorless": False})
    # 単色・多色は無色でない（dmd10-007 天界の神罰「無色ではない」の対象になる）
    assert not e.filter_match(light, {"colorless": True})
    assert e.filter_match(light, {"colorless": False})
    assert not e.filter_match(multi, {"colorless": True})
    assert e.filter_match(multi, {"colorless": False})


def test_empty_civs_still_colorless():
    # civs: [] で登録された無色カード（dmd10-008 等29件）も引き続き無色
    e = build(rules, {"p0": {"bz": ["dmd10-008"]}, "p1": {}, "filler": "T002"})
    cid = e.zlist("bz", 0)[0]
    assert e.chars(cid)["civs"] == []
    assert e.filter_match(cid, {"colorless": True})


def test_pixie_life_returns_zero_card_from_mana():
    # dm24sp2-012 ピクシー・ライフ: 上1枚をマナに置き、無色カード1枚をマナから手札に戻してもよい
    e = build(rules, {"p0": {"hand": ["dm24sp2-012", "T002"],
                             "mana": ["dm24bd2-016", "T004", "T001", "T063"]},
                      "p1": {}, "filler": "T002"})
    yattare = next(c for c in e.zlist("mana", 0) if e.s.cards[c].defn == "dm24bd2-016")
    for _ in range(200):
        d = e.advance()
        if d is None:
            break
        kind, keys = d["kind"], [o["key"] for o in d["options"]]
        if kind == "main" and "play:dm24sp2-012" in keys:
            e.answer([keys.index("play:dm24sp2-012")])
        elif kind == "pay_mana":
            e.answer([0])
        elif kind == "yes_no":
            e.answer([0])                       # 戻す
        elif kind == "choose_cards":
            hit = [i for i, o in enumerate(d["options"]) if o.get("cid") == yattare]
            e.answer(hit[:1] if hit else list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if e.s.cards[yattare].zone == "hand":
            break
    assert e.s.cards[yattare].zone == "hand"    # [zero] のマナカードを戻せた
