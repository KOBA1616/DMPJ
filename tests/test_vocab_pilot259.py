"""第259弾: tap_entry（タップして出してもよい）。"""
from tests.conftest import setup
from dmsim.cards.defs import load_rules


def _summon(e, tap_choice):
    """T697 を召喚し、タップ選択に tap_choice（0=はい/1=いいえ）で答える。"""
    asked = {"yn": False}
    for _ in range(300):
        c = next((c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T697"), None)
        if c is not None and asked["yn"]:
            return e.s.cards[c].tapped
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if any(k.startswith("play:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:"))])
        elif d["kind"] == "yes_no":
            asked["yn"] = True
            e.answer([tap_choice])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("召喚できていない")


def test_summon_tapped_when_chosen():
    e = setup(load_rules(), {"hand": ["T697"], "mana": ["T007", "T007", "T007"]}, {})
    assert _summon(e, 0) is True


def test_summon_untapped_when_declined():
    e = setup(load_rules(), {"hand": ["T697"], "mana": ["T007", "T007", "T007"]}, {})
    assert _summon(e, 1) is False
