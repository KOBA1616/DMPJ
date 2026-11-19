"""第240弾: 常在型 mod gain の展開（置換の付与・誘発の付与）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def test_static_gain_replace_saver():
    e = setup(_rules(), {"bz": ["T650", "T532"]},
              {"hand": ["T006"], "mana": ["T551"] * 3})
    for _ in range(80):
        if "T650" in _defns(e, "graveyard", 0):
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:T006") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T006"))])
        elif d["kind"] == "choose_replacement":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "T532" in _defns(e, "bz", 0)          # ドラゴンは残る
    assert "T650" in _defns(e, "graveyard", 0)   # 付与されたセイバーが身代わり


def test_static_gain_trigger_draw():
    e = setup(_rules(), {"bz": ["T651"], "hand": ["T002"], "mana": ["T002", "T002"]}, {})
    hand_at_play = None
    for _ in range(120):
        if "T002" in _defns(e, "bz", 0) and hand_at_play is not None \
                and len(e.zlist("hand", 0)) == hand_at_play:
            break   # 出した分 -1 と付与誘発のドロー +1 が相殺された
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:T002") for k in keys):
            hand_at_play = len(e.zlist("hand", 0))
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T002"))])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "T002" in _defns(e, "bz", 0)
    assert hand_at_play is not None and len(e.zlist("hand", 0)) == hand_at_play
