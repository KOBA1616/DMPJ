"""第238弾: 常在型 no_lose のイディオム（相手ターン中／タップ時／山札切れのみ）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _pass_turn(e):
    for _ in range(40):
        turn = e.s.turn
        d = e.advance()
        if d is None or e.s.turn != turn:
            return
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


def test_no_lose_only_during_opponent_turn():
    e = setup(_rules(), {"bz": ["T645"]}, {})
    assert e._lose_immune(0, "deck_out") is False     # 自分のターン中は守られない
    _pass_turn(e)                                     # 相手ターンへ
    assert e.s.active == 1
    assert e._lose_immune(0, "deck_out") is True
    assert e._lose_immune(0, "direct_attack") is True
    assert e._lose_immune(1, "deck_out") is False     # 相手は守られない


def test_no_lose_only_while_tapped():
    e = setup(_rules(), {"bz": ["T646"]}, {})
    assert e._lose_immune(0, "deck_out") is False
    cid = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T646")
    e.s.cards[cid].tapped = True
    assert e._lose_immune(0, "deck_out") is True


def test_deck_out_only_scope():
    e = setup(_rules(), {"bz": ["T647"]}, {})
    assert e._lose_immune(0, "deck_out") is True
    assert e._lose_immune(0, "direct_attack") is False
    assert e._lose_immune(0, "effect") is False
