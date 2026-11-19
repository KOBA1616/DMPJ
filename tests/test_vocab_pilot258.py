"""第258弾: alt_cost 混合形（マナ支払い＋シールドを墓地に置く、の両方が要る）。"""
from tests.conftest import setup
from dmsim.cards.defs import load_rules


def test_mixed_alt_cost_charges_both():
    e = setup(load_rules(), {"hand": ["T696"], "mana": ["T034", "T034", "T034", "T034", "T034"]}, {})
    sh_before = len(e.zlist("shield", 0))
    hand_before = len(e.zlist("hand", 0))
    done = {"ok": False}
    for _ in range(300):
        tapped = sum(1 for c in e.zlist("mana", 0) if e.s.cards[c].tapped)
        if len(e.zlist("graveyard", 0)) >= 2 and tapped >= 2:
            done["ok"] = True
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        alt = next((i for i, k in enumerate(keys) if k.endswith(":alt")), None)
        if alt is not None:
            e.answer([alt])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert done["ok"], "代替コストの両方（シールド墓地＋マナ2タップ）が課されていない"
    assert len(e.zlist("shield", 0)) == sh_before - 1          # シールド1つが墓地へ
    assert len(e.zlist("hand", 0)) == hand_before               # 唱えた1枚が墓地へ、ドロー1枚で相殺
