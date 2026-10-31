"""語彙パイロット第18弾（2026-10-31）の検証。

スター進化（rejects: star_evolution）: 面に star: true を宣言する。
離れる時は一番上のカードだけが離れ、下のカードは再構築されてバトルゾーンに残る
（通常の進化クリーチャーは下のカードも一緒に離れる）。
"""
from conftest import setup


def _evolve_star(e):
    """T005 の上に T058 をスター進化させて出す。"""
    for _ in range(25):
        tops = [c for c in e.bz_tops(0) if e.s.cards[c].defn == "T058"]
        if tops:
            return tops[0]
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and "play:T005" in keys:
            e.answer([keys.index("play:T005")])
        elif d["kind"] == "main" and "play:T058" in keys:
            e.answer([keys.index("play:T058")])
        elif d["kind"] == "choose_evo_source":
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("bz:T005"))])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("スター進化クリーチャーが出なかった")


def test_star_evolution_only_top_leaves(rules):
    e = setup(rules, {"hand": ["T005", "T058"], "mana": ["T005"] * 9},
              {"hand": ["T056"], "mana": ["T008"] * 3})
    top = _evolve_star(e)
    base = next(x for x in e.s.zones["bz"][0] if e.s.cards[x].defn == "T005")
    assert e.s.cards[top].under == [base]
    for _ in range(40):   # 相手が破壊呪文でスター進化クリーチャーを狙う
        if e.s.cards[top].zone == "graveyard":
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
    assert e.s.cards[top].zone == "graveyard"      # 一番上のカードだけが離れた
    assert e.s.cards[base].zone == "bz"            # 下のカードはバトルゾーンに残る
    assert base in e.bz_tops(0)                    # 独立したクリーチャーとして扱われる
    assert e.s.cards[base].top_of == -1
