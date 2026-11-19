"""第239弾: break_before（各ブレイクの前に、シールド1枚につき1回）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _attack_and_settle(e, defn):
    for _ in range(120):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and f"attack:{defn}:player" in keys:
            e.answer([keys.index(f"attack:{defn}:player")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if e.s.active != 0 or (d["kind"] == "charge" and e.s.turn > 1):
            return


def test_shieldize_before_each_break():
    e = setup(_rules(), {"bz": ["T648"]}, {})
    shields0 = len(e.zlist("shield", 0))
    opp0 = len(e.zlist("shield", 1))
    _attack_and_settle(e, "T648")
    assert len(e.zlist("shield", 1)) == opp0 - 2          # W・ブレイカーで2枚割れた
    assert len(e.zlist("shield", 0)) == shields0 + 2      # ブレイクの前に1枚ずつシールド化


def test_draw_before_each_break():
    e = setup(_rules(), {"bz": ["T649"]}, {})
    hand0 = len(e.zlist("hand", 0))
    deck0 = len(e.zlist("deck", 0))
    _attack_and_settle(e, "T649")
    # 2ブレイク → 2ドロー（手札はターン開始ドロー等を除きブレイク分だけ増える）
    assert len(e.zlist("deck", 0)) <= deck0 - 2
    assert len(e.zlist("hand", 0)) >= hand0 + 2 - 1       # チャージで1枚置きうる分を差し引く
