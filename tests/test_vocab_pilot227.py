"""第227弾: untap_limit（ターン開始時のアンタップ枚数制限）。

常在型は static の untap_limit キー、呪文の一回性は op untap_limit → s.untap_caps。
上限が候補より小さい時だけ、アンタップするカードの選択が発生する。
"""
from tests.conftest import setup


def _tap_all(e, zone, p):
    cids = [c for c in e.zlist(zone, p)
            if zone != "bz" or e.s.cards[c].controller == p]
    for c in cids:
        e.s.cards[c].tapped = True
    return cids


def _drive_to_untap_choice(e, cap, max_steps=120):
    """相手（P1）のターン開始のアンタップ選択（min=max=cap の choose_cards）まで進める。"""
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] == "choose_cards" and d["player"] == 1 and d["min"] == cap:
            return d
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("untap choice never came")


def _finish_start(e, max_steps=60):
    for _ in range(max_steps):
        d = e.advance()
        if d is None or d["kind"] == "charge":
            return
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


def test_static_bz_cap_1():
    e = setup(_rules(), {"bz": ["T602"]},
              {"bz": ["T002", "T060", "T551"]})
    cids = _tap_all(e, "bz", 1)
    d = _drive_to_untap_choice(e, 1)
    assert len(d["options"]) == 3
    pick = next(i for i, o in enumerate(d["options"]) if "T060" in o["key"])
    e.answer([pick])
    _finish_start(e)
    state = {e.s.cards[c].defn: e.s.cards[c].tapped for c in cids}
    assert state == {"T002": True, "T060": False, "T551": True}   # 選んだ1体だけアンタップ


def test_static_mana_cap_3():
    e = setup(_rules(), {"bz": ["T603"]},
              {"mana": ["T001", "T002", "T030", "T050"]})
    cids = _tap_all(e, "mana", 1)
    d = _drive_to_untap_choice(e, 3)
    assert len(d["options"]) == 4
    picks = [i for i, o in enumerate(d["options"]) if "T050" not in o["key"]]
    e.answer(picks)
    _finish_start(e)
    state = {e.s.cards[c].defn: e.s.cards[c].tapped for c in cids}
    assert state["T050"] is True
    assert sum(1 for v in state.values() if not v) == 3


def test_gate_off_no_cap():
    e = setup(_rules(), {"bz": ["T604"]}, {"bz": ["T002", "T060"]})   # 自分のシールド5つ（既定）
    cids = _tap_all(e, "bz", 1)
    _finish_start(e)   # 選択は発生せず、そのままチャージまで進む
    # チャージ決定に到達した時点で両方アンタップ済みのはず（次の advance で確認）
    assert all(not e.s.cards[c].tapped for c in cids)


def test_gate_on_cap_applies():
    e = setup(_rules(), {"bz": ["T604"], "shield": ["T001", "T001"]},
              {"bz": ["T002", "T060"]})
    cids = _tap_all(e, "bz", 1)
    d = _drive_to_untap_choice(e, 1)
    e.answer([0])
    _finish_start(e)
    assert sum(1 for c in cids if e.s.cards[c].tapped) == 1


def test_spell_one_shot_mana_cap():
    e = setup(_rules(), {"hand": ["T605"], "mana": ["T002", "T002", "T002"]},
              {"mana": ["T001", "T002", "T030"]})
    cids = _tap_all(e, "mana", 1)
    # 呪文を唱える
    for _ in range(60):
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:T605") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T605"))])
            break
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    d = _drive_to_untap_choice(e, 2)
    assert len(d["options"]) == 3
    e.answer([0, 1])
    _finish_start(e)
    assert sum(1 for c in cids if e.s.cards[c].tapped) == 1
    assert e.s.untap_caps == []          # 消費された


def test_min_of_static_and_spell():
    e = setup(_rules(), {"bz": ["T603"], "hand": ["T605"], "mana": ["T002", "T002", "T002"]},
              {"mana": ["T001", "T002", "T030", "T050"]})
    cids = _tap_all(e, "mana", 1)
    for _ in range(60):
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:T605") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T605"))])
            break
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    d = _drive_to_untap_choice(e, 2)     # 常在3 と呪文2 の小さい方
    e.answer([0, 1])
    _finish_start(e)
    assert sum(1 for c in cids if not e.s.cards[c].tapped) == 2


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()
