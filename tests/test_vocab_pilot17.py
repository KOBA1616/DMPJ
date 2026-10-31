"""語彙パイロット第17弾（2026-10-31）の検証。

NEO進化（rejects: neo_evolution）: 面に neo: true と evolve_from を宣言する。
- 通常のクリーチャーとして召喚することも、進化元に重ねて出すこともできる（選択肢が分かれる）
- 重ねて出た時だけ「NEO進化クリーチャーとして扱う」= chars の types に evolution が加わり、
  それを条件にする効果（「NEO進化クリーチャーなら」）が働く
"""
from conftest import setup


def _play(e, key, evo_pick=None):
    for _ in range(20):
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and key in keys:
            e.answer([keys.index(key)])
        elif d["kind"] == "choose_evo_source" and evo_pick is not None:
            e.answer([next(i for i, k in enumerate(keys) if k.startswith(evo_pick))])
            return
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def test_neo_plain_summon_is_not_evolution(rules):
    e = setup(rules, {"hand": ["T057"], "mana": ["T008"] * 5}, {"bz": ["T001"]})
    _play(e, "play:T057")
    for _ in range(10):
        if any(e.s.cards[c].defn == "T057" for c in e.bz_tops(0)):
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    cid = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T057")
    assert "evolution" not in e.chars(cid)["types"]        # 通常召喚では進化クリーチャーではない
    assert any(e.s.cards[c].defn == "T001" for c in e.bz_tops(1))   # 条件効果は働かず、相手は残る


def test_neo_stacked_counts_as_evolution(rules):
    e = setup(rules, {"hand": ["T057"], "bz": ["T008"], "mana": ["T008"] * 5}, {"bz": ["T001", "T008"]})
    d = e.advance()
    while d is not None and d["kind"] != "main":
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
        d = e.advance()
    keys = [o["key"] for o in d["options"]]
    assert "play:T057:neo" in keys                          # 重ねて出す選択肢がある
    _play(e, "play:T057:neo", evo_pick="bz:T008")
    cid = None
    for _ in range(15):
        tops = [c for c in e.bz_tops(0) if e.s.cards[c].defn == "T057"]
        if tops:
            cid = tops[0]
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert cid is not None
    assert e.s.cards[cid].under                          # 進化元が下にある
    assert "evolution" in e.chars(cid)["types"]          # NEO進化クリーチャーとして扱う
    opp = [e.s.cards[c].defn for c in e.bz_tops(1)]
    assert "T001" not in opp                             # 条件効果が働き、闇ではない相手は破壊された
    assert "T008" in opp                                 # 闇の相手は残る
