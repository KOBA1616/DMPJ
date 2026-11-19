"""第257弾: unpaid の拡張（効果で出されたクリーチャーも「マナをタップせずに出た」になる）。"""
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


def _in_shield(e, defn, p=1):
    return any(e.s.cards[c].defn == defn for c in e.zlist("shield", p))


def test_put_entry_shieldized():
    # 効果で「出された」クリーチャーはシールド化される
    e = setup(load_rules(), {"bz": ["T694"]},
              {"hand": ["T693", "T001"], "mana": ["T010"] * 3})
    ok = _drive(e, lambda e: _in_shield(e, "T001"))
    assert ok
    assert not any(e.s.cards[c].defn == "T001" for c in e.zlist("bz", 1))


def test_free_summon_shieldized():
    # コストを支払わずに召喚したクリーチャーもシールド化される
    e = setup(load_rules(), {"bz": ["T694"]},
              {"hand": ["T695", "T001"], "mana": ["T010"] * 3})
    ok = _drive(e, lambda e: _in_shield(e, "T001"))
    assert ok


def test_paid_summon_not_shieldized():
    # 通常召喚（マナをタップして支払った）は対象外（T002 を使う: シールドの filler が T001 のため）
    e = setup(load_rules(), {"bz": ["T694"]},
              {"hand": ["T002"], "mana": ["T007", "T007"]})
    _drive(e, lambda e: any(e.s.cards[c].defn == "T002" for c in e.zlist("bz", 1)))
    _drive(e, lambda e: e.s.active == 0)
    assert any(e.s.cards[c].defn == "T002" for c in e.zlist("bz", 1))
    assert not _in_shield(e, "T002")
