"""第247弾: S・トリガーX — シールドから手札に加わる時、無料ジェネレート＋クロス。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def test_strigger_x_generates_and_crosses():
    # P0: シールドに T670、場に T002。P1 の T534 が攻撃してシールドを割る
    e = setup(_rules(), {"bz": ["T002"], "shield": ["T670"]}, {"bz": ["T534"]})
    gear = next(c for c in e.zlist("shield", 0) if e.s.cards[c].defn == "T670")
    host = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T002")
    for _ in range(300):
        if e.s.cards[gear].crossed:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        atk = next((i for i, k in enumerate(keys) if k.startswith("attack:")), None)
        if atk is not None:
            e.answer([atk])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert gear in e.zlist("bz", 0)                       # ジェネレートされた
    assert e.s.cards[gear].crossed == e.s.ref(host)       # ホストにクロスされた
    ch = e.chars_ro(host)
    assert "triple_breaker" in ch["keywords"]             # T・ブレイカー付与
