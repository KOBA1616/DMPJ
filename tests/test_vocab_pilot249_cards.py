"""第249弾の登録形: dmex18-023 ゴウケンオー ～秘剣轟誕～（ラウンド283）。"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build


def test_registered_stack_from_deck():
    rules = load_rules()
    assert "dmex18-023" in rules.cards
    e = build(rules, {"p0": {"bz": ["dmex18-023"], "deck": ["T001"] * 7 + ["T674"]},
                      "p1": {"deck": ["T001"] * 12},
                      "filler": "T001", "seed": 1, "deck_size": 20})
    atk = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "dmex18-023")
    top = next(c for c in e.zlist("deck", 0) if e.s.cards[c].defn == "T674")
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
    assert e.s.cards[top].zone == "bz"
    assert e.s.cards[atk].top_of == top
    assert atk in e.s.cards[top].under
