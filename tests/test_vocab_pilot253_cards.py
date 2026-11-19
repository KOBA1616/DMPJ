"""第253弾の登録形: hand_discard_protection 4件（ラウンド287）。"""
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
    for cid in ("dm24ex3-051", "dm23rp2x-029", "dmbd04-003", "dmrp08-003"):
        parse_card(copy.deepcopy(_converted(cid)), TABLES)
    def has_ph(ab):
        return ab.get("protect_hand") is True
    assert any(has_ph(a) for a in _converted("dm24ex3-051")["abilities"])
    assert any(has_ph(a) for a in _converted("dmbd04-003")["abilities"])
    assert any(has_ph(a) for a in _converted("dmrp08-003")["faces"][0]["abilities"])


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


def test_registered_nijie_protects_hand():
    rules = load_rules()
    # 登録形の protect_hand: 巡霊者ニージェがいる時、相手の破棄呪文では手札を捨てない
    e = build(rules, {"p0": {"bz": ["dm24ex3-051"], "hand": ["T001", "T002"]},
                      "p1": {"hand": ["T686"], "mana": ["T008", "T008"], "deck": ["T001"] * 10},
                      "filler": "T001", "seed": 1, "deck_size": 14})
    ok = _drive(e, lambda e: any(e.s.cards[c].defn == "T686" for c in e.zlist("graveyard", 1)))
    assert ok, "呪文が唱えられていない"
    assert [e.s.cards[c].defn for c in e.zlist("graveyard", 0)] == []
