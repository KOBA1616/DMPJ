"""第252弾の登録形: dmx17-014 / dmc64-008（ラウンド286）。"""
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
    for cid in ("dmx17-014", "dmc64-008"):
        parse_card(copy.deepcopy(_converted(cid)), TABLES)
    assert _converted("dmx17-014")["keywords"] == ["g_breaker"]


def _cid(e, defn, player):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _drive(e, stop, cross=False, limit=600):
    crossed = {"v": False}
    for _ in range(limit):
        if stop(e):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_breaker":
            e.answer([keys.index("breaks:all") if "breaks:all" in keys else 0])
        elif cross and not crossed["v"] and any(k.startswith("cross:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("cross:"))])
            crossed["v"] = True
        elif any(k.startswith("play:") for k in keys) and d.get("player") == 0:
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:"))])
        else:
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


def test_registered_kaiser_breaks_all():
    rules = load_rules()
    e = build(rules, {"p0": {"bz": ["dmx17-014"]}, "p1": {"deck": ["T001"] * 12},
                      "filler": "T001", "seed": 1, "deck_size": 20})
    _drive(e, stop=lambda e: len(e.zlist("shield", 1)) == 0 and len(e.zlist("shield", 0)) == 0)
    assert len(e.zlist("shield", 1)) == 0
    assert len(e.zlist("shield", 0)) == 0


def test_registered_final_sword_grants():
    rules = load_rules()
    e = build(rules, {"p0": {"bz": ["T002"], "hand": ["dmc64-008"], "mana": ["T008"] * 10},
                      "p1": {"deck": ["T001"] * 12},
                      "filler": "T001", "seed": 1, "deck_size": 20})
    host = _cid(e, "T002", 0)
    _drive(e, cross=True,
           stop=lambda e: len(e.zlist("shield", 1)) == 0 and len(e.zlist("shield", 0)) == 0)
    gear = _cid(e, "dmc64-008", 0)
    assert e.s.cards[gear].crossed[0] == host
    assert len(e.zlist("shield", 1)) == 0
    assert len(e.zlist("shield", 0)) == 0
