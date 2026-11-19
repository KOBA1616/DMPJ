"""第233弾の登録形テスト: launcher_e 再変換5枚（ラウンド269）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["dm20-014", "dm20-023", "dm20-032", "dm20-055", "dm24ex3-rp2tr07"]


def _game(p0, p1):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                         "deck_size": 20})


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _cast(e, spell, tap_count):
    tapped = False
    for _ in range(140):
        if spell in _defns(e, "graveyard", 0):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith(f"play:{spell}") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith(f"play:{spell}"))])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "choose_cards" and not tapped \
                and d.get("min") == 0 and all(k.startswith("bz:") for k in keys):
            tapped = True
            e.answer(list(range(tap_count)))
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("spell did not resolve")


def test_all_registered():
    e = _game({}, {})
    for cid in IDS:
        assert cid in e.rules.cards, cid


def test_014_tap_two_break_two():
    e = _game({"bz": ["T614", "T614"], "hand": ["dm20-014"],
               "mana": ["T050"] * 6}, {})
    before = len(e.zlist("shield", 1))
    _cast(e, "dm20-014", 2)
    assert len(e.zlist("shield", 1)) == before - 2


def test_055_tap_one_mana_plus_one():
    e = _game({"bz": ["T613"], "hand": ["dm20-055"], "mana": ["T002"] * 3}, {})
    before = len(e.zlist("mana", 0))
    _cast(e, "dm20-055", 1)
    assert len(e.zlist("mana", 0)) == before + 1
