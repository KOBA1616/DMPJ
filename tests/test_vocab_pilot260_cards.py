"""第260弾の登録形: mana_civilization_tap 4件（ラウンド294）。"""
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
    for cid in ("dm26ex4-081", "dm24bd6-042", "dm24rp2-074", "dm26rp3-012"):
        c = _converted(cid)
        parse_card(copy.deepcopy(c), TABLES)
        assert any(ab.get("mana_all_civs") for ab in c.get("abilities") or [])
    assert _converted("dm24bd6-042")["abilities"][0]["mana_all_civs"]["for"] == {"partner": True}
    assert "cannot_attack" in _converted("dm24rp2-074")["keywords"]


def test_registered_kototaro_enables_offciv_summon():
    rules = load_rules()
    e = build(rules, {"p0": {"bz": ["dm24rp2-074"], "hand": ["T699"], "mana": ["T010", "T010"],
                             "deck": ["T001"] * 10},
                      "p1": {"deck": ["T001"] * 10},
                      "filler": "T001", "seed": 1, "deck_size": 14})
    entered = {"v": False}
    for _ in range(200):
        if any(e.s.cards[c].defn == "T699" for c in e.zlist("bz", 0)):
            entered["v"] = True
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if any(k.startswith("play:T699") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T699"))])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert entered["v"]
