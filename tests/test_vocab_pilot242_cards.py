"""ラウンド277 登録形: draw_replacement_double（第242弾）。"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build


def _setup(p0, p1=None):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": "T001", "seed": 1, "deck_size": 20})


def _answer(e, d, play_defn=None):
    keys = [o["key"] for o in d["options"]]
    if d["kind"] == "choose_replacement":
        e.answer([0])
    elif play_defn and any(k.startswith(f"play:{play_defn}") for k in keys):
        e.answer([next(i for i, k in enumerate(keys) if k.startswith(f"play:{play_defn}"))])
    elif d["kind"] == "choose_cards" and keys:
        e.answer([0])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def test_dm26rp1_034_double_draw():
    e = _setup({"bz": ["dm26rp1-034"], "hand": ["T001"]})
    h0 = len(e.zlist("hand", 0))
    for _ in range(200):
        if len(e.zlist("hand", 0)) >= h0 + 2:
            break
        d = e.advance()
        assert d is not None
        _answer(e, d)
    assert len(e.zlist("hand", 0)) == h0 + 2


def test_dm28_049_sforce_double_bottom():
    e = _setup({"hand": ["dm28-049", "T001"], "mana": ["T030"] * 4, "shield": ["T001"] * 3})
    for _ in range(200):
        if any(e.s.cards[c].sforce_of for c in e.zlist("shield", 0)):
            break
        d = e.advance()
        assert d is not None
        _answer(e, d, play_defn="dm28-049")
    assert any(e.s.cards[c].sforce_of for c in e.zlist("shield", 0))
    h0 = len(e.zlist("hand", 0))
    for _ in range(240):
        if len(e.zlist("hand", 0)) == h0 + 1 and e.s.active == 0:
            break
        d = e.advance()
        assert d is not None
        _answer(e, d)
    assert len(e.zlist("hand", 0)) == h0 + 1
