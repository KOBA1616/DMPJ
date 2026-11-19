"""第259弾の登録形: tap_entry_option 4件（ラウンド293）。"""
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
    for cid in ("dm26rp1-005", "dm26rp2-044", "dm26rp2-075", "dmrp22-043"):
        c = _converted(cid)
        parse_card(copy.deepcopy(c), TABLES)
        assert c["tap_entry"] is True
    assert _converted("dmrp22-043")["abilities"][1]["mod"]["deny"] == ["attack_player"]


def test_registered_awaza_enters_tapped_by_choice():
    rules = load_rules()
    e = build(rules, {"p0": {"hand": ["dm26rp2-044"], "mana": ["T007"] * 5, "deck": ["T001"] * 10},
                      "p1": {"deck": ["T001"] * 10},
                      "filler": "T001", "seed": 1, "deck_size": 14})
    tapped = {"v": None}
    for _ in range(300):
        c = next((c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "dm26rp2-044"), None)
        if c is not None:
            tapped["v"] = e.s.cards[c].tapped
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if any(k.startswith("play:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:"))])
        elif d["kind"] == "yes_no":
            e.answer([0])   # タップして出す
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert tapped["v"] is True
