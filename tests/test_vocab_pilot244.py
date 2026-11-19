"""第244弾: 常在型 gain で得た常在型の mod（バトルパワー）が chars に効く。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def test_gained_battle_power_applies():
    # T661 がドラゴン（T662）に battle_power +6000 を付与 → 2000+6000 で T004（3000）に勝つ
    e = setup(_rules(), {"bz": ["T661", "T662"]}, {"bz": ["T004"]})
    t662 = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T662")
    t004 = next(c for c in e.zlist("bz", 1) if e.s.cards[c].defn == "T004")
    e.s.cards[t004].tapped = True
    for _ in range(120):
        if t004 in e.zlist("graveyard", 1):
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        atk = next((i for i, k in enumerate(keys) if k == "attack:T662:T004"), None)
        if atk is not None:
            e.answer([atk])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")] if "no_block" in keys else list(range(d.get("min", 0))))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert t004 in e.zlist("graveyard", 1)      # バトルに勝った
    assert t662 in e.zlist("bz", 0)             # T662 は残る
