"""第257弾の登録形: entry_without_mana_tap 4件（ラウンド291）。"""
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


def test_registered_forms():
    for cid in ("dm26ex4-083", "dm26ex4-070", "dm26rp1-std001", "dm26sd1-s011"):
        c = _converted(cid)
        parse_card(copy.deepcopy(c), TABLES)
        trig = c["abilities"][0] if cid != "dm26rp1-std001" else c["abilities"][-1]
        assert trig["when"]["unpaid"] is True


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


def test_registered_hodoyo_shieldizes_put_creature():
    rules = load_rules()
    e = build(rules, {"p0": {"bz": ["dm26ex4-083"]},
                      "p1": {"hand": ["T693", "T002"], "mana": ["T010"] * 3, "deck": ["T001"] * 10},
                      "filler": "T001", "seed": 1, "deck_size": 14})
    ok = _drive(e, lambda e: any(e.s.cards[c].defn == "T002" for c in e.zlist("shield", 1)))
    assert ok
    assert not any(e.s.cards[c].defn == "T002" for c in e.zlist("bz", 1))
