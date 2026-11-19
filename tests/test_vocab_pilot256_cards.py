"""第256弾の登録形: dm24ex4-066（ラウンド290）。"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card
from dmsim.scenario import build

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)


def _converted(cid):
    import yaml
    for c in yaml.safe_load(open(CONVERTED))["cards"]:
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def test_registered_form():
    c = _converted("dm24ex4-066")
    parse_card(copy.deepcopy(c), TABLES)
    w = c["faces"][0]["abilities"][0]["when"]
    assert w["not_reason"] == "summon"
    assert c["faces"][1]["spell"][0]["op"] == "action_limit"


def _drive(e, stop, limit=400):
    for _ in range(limit):
        if stop(e):
            return True
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if any(k.startswith("play:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:"))])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return stop(e)


def test_registered_sage_bounces_put_creature():
    rules = load_rules()
    e = build(rules, {"p0": {"bz": ["dm24ex4-066"]},
                      "p1": {"hand": ["T693", "T001"], "mana": ["T010"] * 3, "deck": ["T001"] * 10},
                      "filler": "T001", "seed": 1, "deck_size": 14})
    ok = _drive(e, lambda e: any(e.s.cards[c].defn == "T693" for c in e.zlist("graveyard", 1)))
    assert ok, "呪文が唱えられていない"
    _drive(e, lambda e: e.s.active == 0)
    assert not any(e.s.cards[c].defn == "T001" for c in e.zlist("bz", 1))
    assert any(e.s.cards[c].defn == "T001" for c in e.zlist("hand", 1))
