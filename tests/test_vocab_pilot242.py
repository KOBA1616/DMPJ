"""第242弾: draw_replacement_double（ドロー置換の倍化イディオム）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _drive_until(e, stop, limit=160, decline_replacement=False):
    for _ in range(limit):
        if stop():
            return True
        d = e.advance()
        if d is None:
            return stop()
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_replacement":
            if decline_replacement and "decline" in keys:
                e.answer([keys.index("decline")])
            else:
                e.answer([0])
        elif d["kind"] == "choose_cards" and keys:
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return stop()


def test_plain_double_on_turn_draw():
    # T657 がいる時、ターンのはじめのドローが2枚になる（P0 は2ターン目から引く）
    e = setup(_rules(), {"bz": ["T657"], "hand": ["T001"]}, {})
    h0 = len(e.zlist("hand", 0))
    ok = _drive_until(e, lambda: len(e.zlist("hand", 0)) >= h0 + 2)
    assert ok and len(e.zlist("hand", 0)) == h0 + 2


def test_plain_double_declined():
    e = setup(_rules(), {"bz": ["T657"], "hand": ["T001"]}, {})
    h0 = len(e.zlist("hand", 0))
    # 置換を断ると通常の1枚ドロー（相手ターン→自ターンで +1 のまま安定）
    seen = []
    for _ in range(200):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_replacement":
            e.answer([keys.index("decline")])
            seen.append(len(e.zlist("hand", 0)))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if seen and len(e.zlist("hand", 0)) == h0 + 1:
            break
    assert seen and len(e.zlist("hand", 0)) == h0 + 1


def test_sforce_double_and_bottom():
    # T658: 手札から出すとシールドとリンク → 以後のドローは2枚引いて1枚を山札の下へ
    e = setup(_rules(), {"hand": ["T658", "T001"], "mana": ["T030"] * 4, "shield": ["T001"] * 3}, {})
    for _ in range(160):
        if any(e.s.cards[c].sforce_of for c in e.zlist("shield", 0)):
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        play = next((i for i, k in enumerate(keys) if k.startswith("play:T658")), None)
        if play is not None:
            e.answer([play])
        elif d["kind"] == "choose_cards" and keys:
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert any(e.s.cards[c].sforce_of for c in e.zlist("shield", 0))
    h0 = len(e.zlist("hand", 0))
    # 次の自分のターンのはじめ: +2 -1 = +1（下に置いた分はデッキへ）
    ok = _drive_until(e, lambda: len(e.zlist("hand", 0)) == h0 + 1 and e.s.active == 0)
    assert ok
