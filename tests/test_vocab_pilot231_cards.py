"""第231弾の登録形テスト: evolution_v_two_bases 再変換4枚（ラウンド267）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["dm22-024", "dm22-027", "dm12-005", "dm12-s03"]


def _game(p0, p1):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                         "deck_size": 20})


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def test_all_registered():
    e = _game({}, {})
    for cid in IDS:
        assert cid in e.rules.cards, cid


def test_phoenix_evolves_on_two_bases():
    e = _game({"bz": ["T624", "T625"], "hand": ["dm12-005"],
               "mana": ["T551", "T551", "T002", "T002"]}, {})
    for _ in range(140):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:dm12-005") for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if k.startswith("play:dm12-005"))])
        elif d["kind"] in ("pay_mana", "choose_evo_source"):
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if "dm12-005" in _defns(e, "bz", 0):
            break
    assert "dm12-005" in _defns(e, "bz", 0)
    top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "dm12-005")
    assert len(e.s.cards[top].under) == 2
    assert len(e.s.cards[top].stack_bases) == 2
    assert {e.s.cards[u].defn for u in e.s.cards[top].under} == {"T624", "T625"}
