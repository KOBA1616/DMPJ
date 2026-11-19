"""第237弾: エクストラEXライフ（紐付けシールド2枚、離れる時は1枚ずつ肩代わり）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _drive(e, spell=None, max_steps=200):
    """T006（破壊呪文）で T643 を狙い続けるための汎用ドライバ。"""
    for _ in range(max_steps):
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and spell and any(k.startswith(f"play:{spell}") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith(f"play:{spell}"))])
            return
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


def _enter(e):
    shields0 = len(e.zlist("shield", 0))
    for _ in range(80):
        if "T643" in _defns(e, "bz", 0):
            return shields0
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:T643") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T643"))])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("T643 did not enter")


def _linked(e):
    top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T643")
    ref = e.s.ref(top)
    return [c for c in e.zlist("shield", 0)
            if e.s.cards[c].exlife_of is not None and list(e.s.cards[c].exlife_of) == list(ref)]


def test_two_shields_linked_and_consumed_one_by_one():
    e = setup(_rules(), {"hand": ["T643"], "mana": ["T030"] * 5},
              {"hand": ["T006"], "mana": ["T551"] * 3})
    shields0 = _enter(e)
    assert len(e.zlist("shield", 0)) == shields0 + 2      # 2枚シールド化
    assert len(_linked(e)) == 2
    # 相手ターンに T006 で破壊を試みる → シールド1枚が肩代わりして残る
    for _ in range(60):
        if len(_linked(e)) == 1:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:T006") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T006"))])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "T643" in _defns(e, "bz", 0)                   # 本体は残る
    assert len(_linked(e)) == 1                          # 紐付けは残り1枚


def test_exlife_filter_grants_strigger_to_linked_shields():
    # フィルタ exlife: 紐付いたシールドだけに S・トリガーが付く
    e = setup(_rules(), {"hand": ["T643"], "mana": ["T030"] * 5, "bz": ["T644"]}, {})
    _enter(e)
    linked = _linked(e)
    assert len(linked) == 2
    assert all("s_trigger" in e.chars_ro(c)["keywords"] for c in linked)
    plain = [c for c in e.zlist("shield", 0) if c not in linked]
    assert plain and all("s_trigger" not in e.chars_ro(c)["keywords"] for c in plain)
