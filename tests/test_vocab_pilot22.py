"""語彙パイロット第22弾（2026-10-31）の検証。

クロスギア（rejects: cross_gear、単独60件）は既存実装で表せることの確認（新規実装なし）。
- クロスギアをジェネレートし、メインステップでコストをもう一度支払ってクリーチャーにクロスする
- クロスしたクリーチャーへの常在型は affects: crossed で書き、パワー修正とキーワード付与が及ぶ
- クロス先のクリーチャーが離れても、クロスギアはバトルゾーンに残る
"""
from conftest import setup


def _to_main_with(e, key):
    for _ in range(30):
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and key in keys:
            return d, keys
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError(key)


def test_cross_gear_cycle(rules):
    e = setup(rules, {"hand": ["T062"], "bz": ["T001"], "mana": ["T001"] * 4},
              {"hand": ["T056"], "mana": ["T008"] * 3})
    creature = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T001")
    assert e.chars(creature)["power"] == 2000 and "blocker" not in e.chars(creature)["keywords"]
    d, keys = _to_main_with(e, "play:T062")          # クロスギアをジェネレートする
    e.answer([keys.index("play:T062")])
    gear = None
    for _ in range(15):
        tops = [c for c in e.bz_tops(0) if e.s.cards[c].defn == "T062"]
        if tops:
            gear = tops[0]
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert gear is not None
    d, keys = _to_main_with(e, "cross:T062:T001")    # コストをもう一度支払ってクロスする
    e.answer([keys.index("cross:T062:T001")])
    for _ in range(10):
        if e.s.cards[gear].crossed:
            break
        d = e.advance()
        if d is None:
            break
        e.answer(list(range(d["min"])))
    assert e.s.cards[gear].crossed and e.s.cards[gear].crossed[0] == creature
    ch = e.chars(creature)
    assert ch["power"] == 3500 and "blocker" in ch["keywords"]   # クロスしたクリーチャーだけが強化される
    # クロス先が破壊されても、クロスギアは残る
    for _ in range(40):
        if e.s.cards[creature].zone == "graveyard":
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d["player"] == 1 and "play:T056" in keys:
            e.answer([keys.index("play:T056")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert e.s.cards[creature].zone == "graveyard"
    assert e.s.cards[gear].zone == "bz"
