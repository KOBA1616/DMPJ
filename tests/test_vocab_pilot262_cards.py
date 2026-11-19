"""第262弾の登録形: ninja_change 5件（ラウンド296）。"""
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
    for cid in ("dm23sd2-001", "dm25ex1-014", "dm25ex1-034", "dm25ex1-mc009", "dm26sd1-s001"):
        c = _converted(cid)
        parse_card(copy.deepcopy(c), TABLES)
        groups = [ab.get("group") for ab in c.get("abilities") or [] if ab.get("kind") == "declare"]
        assert groups == ["ninja", "ninja"], (cid, groups)


def test_registered_ninja_change_on_opponent_attack():
    rules = load_rules()
    e = build(rules, {"p0": {"bz": ["dm23sd2-001"], "hand": ["dm26sd1-s001"], "deck": ["T001"] * 10},
                      "p1": {"bz": ["T001"], "deck": ["T001"] * 10},
                      "filler": "T001", "seed": 1, "deck_size": 14})
    swapped = {"v": False}
    for _ in range(400):
        if any(e.s.cards[c].defn == "dm26sd1-s001" for c in e.zlist("bz", 0)):
            swapped["v"] = True
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"].startswith("declare"):
            hit = next((i for i, k in enumerate(keys) if k.startswith("declare:dm26sd1-s001")), None)
            e.answer([hit] if hit is not None else [])
        elif d["kind"] == "attack":
            atk = next((i for i, k in enumerate(keys) if k.startswith("attack:T001")), None)
            if atk is not None and e.s.active == 1:
                e.answer([atk])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert swapped["v"]
    assert any(e.s.cards[c].defn == "dm23sd2-001" for c in e.zlist("hand", 0))
