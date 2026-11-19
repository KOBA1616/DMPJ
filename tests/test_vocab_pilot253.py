"""第253弾: protect_hand（相手の呪文やクリーチャーの能力では手札を捨てられない）。

判定は相手プレイヤーの墓地ではなく「自分の墓地に捨てられたカードがあるか」で見る
（ドローで手札枚数が動くため）。"""
from tests.conftest import setup
from dmsim.cards.defs import load_rules


def _drive(e, stop, limit=400):
    for _ in range(limit):
        if stop(e):
            return True
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if any(k.startswith("play:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:"))])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return stop(e)


def _grave0(e):
    return [e.s.cards[c].defn for c in e.zlist("graveyard", 0)]


def test_spell_discard_blocked():
    e = setup(load_rules(), {"hand": ["T001", "T002"], "bz": ["T685"]},
              {"hand": ["T686"], "mana": ["T008", "T008"]})
    ok = _drive(e, lambda e: any(e.s.cards[c].defn == "T686" for c in e.zlist("graveyard", 1)))
    assert ok, "呪文が唱えられていない"
    assert _grave0(e) == []          # 呪文による破棄は防がれる


def test_creature_ability_discard_blocked():
    e = setup(load_rules(), {"hand": ["T001", "T002"], "bz": ["T685"]},
              {"hand": ["T687"], "mana": ["T008"] * 4})
    ok = _drive(e, lambda e: any(e.s.cards[c].defn == "T687" for c in e.zlist("bz", 1)))
    assert ok
    _drive(e, lambda e: e.s.active == 0)   # 誘発の解決まで進める
    assert _grave0(e) == []          # クリーチャーの能力による破棄も防がれる


def test_tamaseed_ability_discard_not_blocked():
    e = setup(load_rules(), {"hand": ["T001", "T002"], "bz": ["T685"]},
              {"hand": ["T688"], "mana": ["T008"] * 4})
    ok = _drive(e, lambda e: any(e.s.cards[c].defn == "T688" for c in e.zlist("bz", 1)))
    assert ok
    _drive(e, lambda e: len(_grave0(e)) == 1)
    assert len(_grave0(e)) == 1      # タマシードの能力は保護の対象外


def test_no_protector_discard_works():
    e = setup(load_rules(), {"hand": ["T001", "T002"]},
              {"hand": ["T686"], "mana": ["T008", "T008"]})
    ok = _drive(e, lambda e: any(e.s.cards[c].defn == "T686" for c in e.zlist("graveyard", 1)))
    assert ok
    assert len(_grave0(e)) == 1      # 保護がなければ通常どおり捨てられる
