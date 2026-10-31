"""語彙パイロット第24弾（2026-10-31）の検証: フェーズ2（攻撃時すげ替え系）。

- 革命チェンジ: declare + swap（既存）の型で、攻撃クリーチャーと手札を入れ替え、攻撃が続く
- 侵略: 新 op invade。手札のクリーチャーを攻撃中のクリーチャーの上に重ね、攻撃が続く（ETBも誘発）
- アタック・チャンス: declare + play_free（既存）の型で、攻撃時に手札の呪文を無償で唱える
- J・チェンジ: swap の拡張（out_to: mana + 入る側の選択）。攻撃クリーチャーとマナゾーンのクリーチャーを入れ替える
"""
from conftest import setup


def _drive(e, want_defn, done, max_steps=90):
    """攻撃を進め、want_defn を含む選択肢が出たらそれを選ぶ（yes_no は yes）。done(e) で終了。"""
    for _ in range(max_steps):
        if done(e):
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        hit = [i for i, k in enumerate(keys) if want_defn in k and not k.startswith("charge:")]
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
    return done(e)


def _attacker(e, defn="T063"):
    e.s.cards[next(c for c in e.bz_tops(0) if e.s.cards[c].defn == defn)].entered_turn = -1


def test_revolution_change(rules):
    e = setup(rules, {"bz": ["T063"], "hand": ["T064"]}, {"shield": ["T001", "T001"]})
    _attacker(e)
    ok = _drive(e, "T064", lambda e: any(e.s.cards[c].defn == "T064" for c in e.bz_tops(0)) and len(e.zlist("shield", 1)) == 1)
    assert ok, "革命チェンジで出なかった"
    assert any(e.s.cards[c].defn == "T063" for c in e.zlist("hand", 0))     # 元の攻撃クリーチャーは手札へ
    assert len(e.zlist("shield", 1)) == 1                                    # 攻撃は新しいクリーチャーで続いた


def test_invasion(rules):
    e = setup(rules, {"bz": ["T063"], "hand": ["T065"], "deck": ["T001"]}, {"shield": ["T001", "T001"]})
    _attacker(e)
    base_hand = len(e.zlist("hand", 0))
    ok = _drive(e, "T065", lambda e: any(e.s.cards[c].defn == "T065" for c in e.bz_tops(0)) and len(e.zlist("shield", 1)) == 1)
    assert ok, "侵略で重ならなかった"
    top = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T065")
    assert e.s.cards[top].under and e.s.cards[e.s.cards[top].under[0]].defn == "T063"   # 攻撃クリーチャーが下に
    assert len(e.zlist("shield", 1)) == 1                                    # 攻撃が続いた
    assert len(e.zlist("hand", 0)) == base_hand                              # ETB ドローで手札が戻った（-1+1）


def test_attack_chance(rules):
    e = setup(rules, {"bz": ["T063"], "hand": ["T066"], "deck": ["T001", "T001"]}, {"shield": ["T001", "T001"]})
    _attacker(e)
    ok = _drive(e, "T066", lambda e: any(e.s.cards[c].defn == "T066" for c in e.zlist("graveyard", 0)) and len(e.zlist("shield", 1)) == 1)
    assert ok, "アタック・チャンスで唱えられなかった"
    assert len(e.zlist("shield", 1)) == 1                                    # 攻撃も続いた


def test_j_change(rules):
    e = setup(rules, {"bz": ["T067"], "mana": ["T068", "T001", "T001"]}, {"shield": ["T001", "T001"]})
    _attacker(e, "T067")
    ok = _drive(e, "T068", lambda e: any(e.s.cards[c].defn == "T068" for c in e.bz_tops(0)) and len(e.zlist("shield", 1)) == 1)
    assert ok, "J・チェンジで入れ替わらなかった"
    assert any(e.s.cards[c].defn == "T067" for c in e.zlist("mana", 0))     # 元のクリーチャーはマナゾーンへ
    assert len(e.zlist("shield", 1)) == 1                                    # 攻撃は入れ替わったクリーチャーで続いた
