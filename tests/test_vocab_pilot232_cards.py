"""第232弾の登録形テスト: evolution_base_any_race 再変換4枚（ラウンド268）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["dm22-019", "dm23-034", "dm14-037", "dm32-110"]


def _game(p0, p1):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                         "deck_size": 20})


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _evolve_dragon(e, base):
    for _ in range(140):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:T627") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T627"))])
        elif d["kind"] in ("pay_mana", "choose_evo_source"):
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if "T627" in _defns(e, "bz", 0):
            top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T627")
            assert [e.s.cards[u].defn for u in e.s.cards[top].under] == [base]
            return True
    return False


def test_all_registered():
    e = _game({}, {})
    for cid in IDS:
        assert cid in e.rules.cards, cid


def test_inos_accepts_dragon_evolution():
    e = _game({"bz": ["dm22-019"], "hand": ["T627"], "mana": ["T551"] * 4}, {})
    assert _evolve_dragon(e, "dm22-019")


def test_metamorph_needs_seven_mana():
    # マナ7枚以上で得る（メタモーフ）: 7枚あるので置ける
    e = _game({"bz": ["dm14-037"], "hand": ["T627"],
               "mana": ["T551"] * 4 + ["T001"] * 3}, {})
    assert _evolve_dragon(e, "dm14-037")
