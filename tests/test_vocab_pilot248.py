"""第248弾: ブレイク前にそのシールドの呪文を差し替えて無料で唱える（break_before + event.shield）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _attack(e, stop, cap=300):
    for _ in range(cap):
        if stop():
            return True
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        atk = next((i for i, k in enumerate(keys) if k.startswith("attack:")), None)
        if atk is not None:
            e.answer([atk])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return stop()


def test_intercept_casts_shield_spell():
    # P1 のシールドが呪文 T672: 差し替えて P0 が唱え（2ドロー）、呪文は P1 の墓地へ。シールドは1枚減る
    e = setup(_rules(), {"bz": ["T671"], "hand": []}, {"shield": ["T672", "T001", "T001"]})
    sp = next(c for c in e.zlist("shield", 1) if e.s.cards[c].defn == "T672")
    hand0 = len(e.zlist("hand", 0))
    ok = _attack(e, lambda: sp in e.zlist("graveyard", 1))
    assert ok, "シールドの呪文が唱えられなかった"
    assert len(e.zlist("hand", 0)) == hand0 + 2          # 唱えた P0 が2枚引く
    assert len(e.zlist("shield", 1)) == 0                # T・ブレイカーで3枚ともブレイク成立（呪文以外は通常どおり手札へ）
    assert sp not in e.zlist("hand", 1)                  # 差し替えたシールドは手札に行かない


def test_creature_shield_breaks_normally():
    # シールドがクリーチャーなら差し替えは起きず、通常どおり手札へ
    e = setup(_rules(), {"bz": ["T671"]}, {"shield": ["T002", "T001"]})
    cr = next(c for c in e.zlist("shield", 1) if e.s.cards[c].defn == "T002")
    ok = _attack(e, lambda: cr in e.zlist("hand", 1))
    assert ok
    assert len(e.zlist("shield", 1)) == 0                # 2枚ともブレイクされ手札へ（差し替えなし）
