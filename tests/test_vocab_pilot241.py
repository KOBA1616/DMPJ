"""第241弾: cross_reduce（ギア側／ホスト側／全体のクロスコスト軽減）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _cross(e, gear, host, pay_pick):
    """gear を host にクロスする。支払いの組が1通りだけなら pay_mana は自動解決される。"""
    crossed = False
    for _ in range(80):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        ck = f"cross:{gear}:{host}"
        if d["kind"] == "main" and ck in keys:
            e.answer([keys.index(ck)])
            crossed = True
        elif d["kind"] == "pay_mana":
            sizes = [len(o["key"].split(",")) if o["key"] != "mana:" else 0 for o in d["options"]]
            e.answer([pay_pick(sizes)])
            d2 = e.advance()   # 支払いのタップが反映されるまで進める
            if d2 is not None and "pass" in [o["key"] for o in d2["options"]]:
                pass
            return
        elif crossed:
            return   # 支払いが自動解決され、次のステップに移った
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("cross did not happen")


def _tapped_mana(e):
    return sum(1 for c in e.zlist("mana", 0) if e.s.cards[c].tapped)


def test_gear_side_may_reduce_to_samurai():
    # T652（コスト4、サムライへは最大2軽減・下限1）→ T655（サムライ）
    e = setup(_rules(), {"bz": ["T652", "T655"], "mana": ["T551"] * 6}, {})
    _cross(e, "T652", "T655", lambda sizes: sizes.index(min(sizes)))
    assert _tapped_mana(e) == 2   # 4 - 2 = 2


def test_gear_side_no_reduce_to_non_samurai():
    e = setup(_rules(), {"bz": ["T652", "T002"], "mana": ["T551"] * 6}, {})
    _cross(e, "T652", "T002", lambda sizes: sizes.index(min(sizes)))
    assert _tapped_mana(e) == 4   # サムライでないので軽減なし


def test_host_side_reduce():
    # T656（コスト3）→ T653（ホスト側で1軽減・下限1）
    e = setup(_rules(), {"bz": ["T656", "T653"], "mana": ["T002"] * 4}, {})
    _cross(e, "T656", "T653", lambda sizes: sizes.index(min(sizes)))
    assert _tapped_mana(e) == 2   # 3 - 1 = 2


def test_global_reduce():
    # T654 がいる間、T656（コスト3）→ T002 は1軽減
    e = setup(_rules(), {"bz": ["T656", "T654", "T002"], "mana": ["T002"] * 4}, {})
    _cross(e, "T656", "T002", lambda sizes: sizes.index(min(sizes)))
    assert _tapped_mana(e) == 2   # 3 - 1 = 2
