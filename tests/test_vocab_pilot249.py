"""第249弾: 山札から見たクリーチャーを自分の上に重ねる（stack_evo + evo_source）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def test_stack_from_deck_on_attack():
    e = setup(_rules(), {"bz": ["T673"], "deck": ["T001"] * 7 + ["T674"]}, {})
    atk = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T673")
    top = next(c for c in e.zlist("deck", 0) if e.s.cards[c].defn == "T674")
    deck_n = len(e.zlist("deck", 0))
    for _ in range(300):
        if e.s.cards[top].zone == "bz":
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        a = next((i for i, k in enumerate(keys) if k.startswith("attack:")), None)
        if a is not None:
            e.answer([a])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert e.s.cards[top].zone == "bz"                    # 山札から場に出た
    assert e.s.cards[atk].top_of == top                   # 攻撃クリーチャーの上に重なった
    assert atk in e.s.cards[top].under
    assert len(e.zlist("deck", 0)) == deck_n - 1          # 残りは戻してシャッフル（枚数は重ねた1枚だけ減る）
