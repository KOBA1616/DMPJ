"""第228弾: crystal_charger（水晶チャージャー）。

唱えた後、墓地のかわりに裏向きでマナゾーンへ置く。通常チャージャーは表向き。
"""
from tests.conftest import setup


def _cast(e, defn, max_steps=80):
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith(f"play:{defn}") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith(f"play:{defn}"))])
            return
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("never cast")


def _settle(e, pred, max_steps=40):
    for _ in range(max_steps):
        if pred(e):
            return
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("did not settle")


def _in_mana(e, defn):
    return [c for c in e.zlist("mana", 0) if e.s.cards[c].defn == defn]


def test_crystal_charger_goes_to_mana_face_down():
    e = setup(_rules(), {"hand": ["T607"], "mana": ["T030", "T001"]}, {})
    _cast(e, "T607")
    _settle(e, lambda e: _in_mana(e, "T607"))
    got = _in_mana(e, "T607")
    assert len(got) == 1
    assert e.s.cards[got[0]].face_down is True          # 裏向きでマナへ
    assert not [c for c in e.zlist("graveyard", 0) if e.s.cards[c].defn == "T607"]
    assert len(e.zlist("hand", 0)) == 1                 # 効果で1枚引いている


def test_plain_charger_goes_to_mana_face_up():
    e = setup(_rules(), {"hand": ["T608"], "mana": ["T030", "T001"]}, {})
    _cast(e, "T608")
    _settle(e, lambda e: _in_mana(e, "T608"))
    got = _in_mana(e, "T608")
    assert len(got) == 1
    assert e.s.cards[got[0]].face_down is False         # 通常チャージャーは表向き


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()
