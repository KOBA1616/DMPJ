"""第258弾の登録形: cast_time_alternative_cost 3件（ラウンド292）。"""
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
    for cid in ("dm24ex3-rp3s11", "dm24ex3-tf20", "dm24ex4-060"):
        parse_card(copy.deepcopy(_converted(cid)), TABLES)
    assert _converted("dm24ex3-rp3s11")["alt_cost"]["cost"] == 4
    assert _converted("dm24ex3-rp3s11")["alt_cost"]["do"][0]["zone"] == "shield"
    assert _converted("dm24ex3-tf20")["alt_cost"]["do"][0]["tap"] is True
    assert _converted("dm24ex4-060")["alt_cost"]["if"]


def test_registered_yume_distributes_top_four():
    rules = load_rules()
    e = build(rules, {"p0": {"hand": ["dm24ex3-tf20"], "mana": ["T001"] * 5, "deck": ["T002"] * 12},
                      "p1": {"deck": ["T001"] * 10},
                      "filler": "T001", "seed": 1, "deck_size": 16})
    top4 = set(e.zlist("deck", 0)[:4])
    assert len(top4) == 4
    state = {"done": False}
    for _ in range(400):
        if state["done"]:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if any(e.s.cards[c].defn == "dm24ex3-tf20" for c in e.zlist("graveyard", 0)):
            state["done"] = True
            break
        play = next((i for i, k in enumerate(keys) if k.startswith("play:dm24ex3-tf20") and ":alt" not in k), None)
        if play is not None:
            e.answer([play])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert state["done"]
    in_hand = [c for c in top4 if e.s.cards[c].zone == "hand"]
    in_mana = [c for c in top4 if e.s.cards[c].zone == "mana"]
    in_deck = [c for c in top4 if e.s.cards[c].zone == "deck"]
    assert len(in_hand) == 1 and len(in_mana) == 1 and len(in_deck) == 2
