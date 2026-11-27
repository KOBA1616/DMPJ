"""語彙パイロット第25弾（2026-11-01）の検証: フェーズ3（フィールド系）。

- D2フィールド: フィールドはバトルゾーンに1枚だけ。新しいフィールドが出たら他のフィールドは破壊される
- D・D・D: declare + play_self（キリフダッシュと同じ型）で、攻撃時に代替コストを払って手札から実行できる
- G・城: galaxy_shield 宣言 + シールドゾーンで働く常在型 + 離脱置換（表向きで離れる時は墓地へ）
"""
from conftest import setup


def _play(e, key, max_steps=40):
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and key in keys:
            e.answer([keys.index(key)])
            return
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError(key)


def _settle(e, done, max_steps=40):
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    return done()


def test_normal_fields_have_no_limit(rules):
    """D2 でないフィールドに枚数制限は無い（703.4l は D2 だけ。2026-11-27 koba 裁定）。旧テストは通常フィールド同士も1枚としていた。"""
    e = setup(rules, {"hand": ["T069", "T070"], "mana": ["T005", "T005", "T001", "T001"], "deck": ["T001"]}, {})
    _play(e, "play:T069")
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T069" for c in e.bz_tops(0)))
    _play(e, "play:T070")
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T070" for c in e.bz_tops(0)))
    assert any(e.s.cards[c].defn == "T069" for c in e.bz_tops(0)), "通常フィールドが破壊された（制限は D2 だけ）"
    assert not any(e.s.cards[c].defn == "T069" for c in e.zlist("graveyard", 0))


def test_d_d_d(rules):
    e = setup(rules, {"bz": ["T001"], "hand": ["T071"], "mana": ["T003", "T003", "T003"]},
              {"shield": ["T001", "T001"]})
    e.s.cards[next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T001")].entered_turn = -1
    done = lambda: any(e.s.cards[c].defn == "T071" for c in e.bz_tops(0))
    for _ in range(60):
        if done():
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        hit = [i for i, k in enumerate(keys) if "T071" in k and not k.startswith("charge:")]
        if hit and d["kind"] not in ("pay_mana", "charge"):
            e.answer([hit[0]])
        elif d["kind"] == "yes_no" and "yes" in keys:
            e.answer([keys.index("yes")])
        elif d["kind"] == "attack":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert done(), "D・D・D で出なかった"
    assert sum(1 for c in e.zlist("mana", 0) if e.s.cards[c].tapped) == 3   # 代替コスト3を払った


def test_g_castle(rules):
    e = setup(rules, {"hand": ["T072"], "bz": ["T001"], "mana": ["T004", "T004"]}, {"bz": ["T005"]})
    e.s.cards[next(c for c in e.bz_tops(1) if e.s.cards[c].defn == "T005")].entered_turn = -1
    _play(e, "play:T072:gshield")
    ok = _settle(e, lambda: any(e.s.cards[c].defn == "T072" and e.s.cards[c].face_up
                                for c in e.zlist("shield", 0)))
    assert ok, "G・城が表向きシールドにならなかった"
    creature = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T001")
    assert e.chars(creature)["power"] == 3000        # 表向きシールドの間の常在型（2000+1000）
    # 相手が攻撃してこのシールドがブレイクされる → 手札ではなく墓地へ（離脱置換）
    e.s.cards[creature].entered_turn = 99            # 自分は攻撃しない
    ok = False
    for _ in range(90):
        if any(e.s.cards[c].defn == "T072" for c in e.zlist("graveyard", 0)):
            ok = True
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and d["player"] == 1:
            e.answer([0])                            # 相手は攻撃する
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert ok, "表向きで離れる時に墓地へ置かれなかった"
