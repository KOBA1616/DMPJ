"""第261弾の登録形: CIP使用系4件（ラウンド295）。"""
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
    for cid in ("dmrp08-010", "dm25ex3-rp3007", "promoy17-sp4d01", "dm26ex4-cho005"):
        parse_card(copy.deepcopy(_converted(cid)), TABLES)
    assert _converted("dm26ex4-cho005")["abilities"][-1] == {"kind": "static", "cast_limit": {"count": 1}}
    assert "dm26sd1-n001" in _converted("dm26ex4-cho005")["source"]["aliases"]


def test_registered_pack_leeman_uses_cip():
    rules = load_rules()
    e = build(rules, {"p0": {"hand": ["dmrp08-010"], "mana": ["T007"] * 9, "deck": ["T001"] * 10},
                      "p1": {"bz": ["T702", "T001"], "deck": ["T001"] * 10},
                      "filler": "T001", "seed": 1, "deck_size": 14})
    hand0 = {"n": None}
    for _ in range(600):
        if hand0["n"] is not None and len(e.zlist("hand", 0)) > hand0["n"]:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if any(k.startswith("play:dmrp08-010") for k in keys):
            hand0["n"] = len(e.zlist("hand", 0))
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:dmrp08-010"))])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif d["kind"] == "use_entry":
            e.answer([0])   # T702 の「引く」能力を使う
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(min(d.get("max", d.get("min", 0)), len(keys)))))
    # 相手の2体はマナへ行き、T702 のドロー能力で自分の手札が増えた
    assert hand0["n"] is not None and len(e.zlist("hand", 0)) > hand0["n"]
    assert sum(1 for c in e.zlist("mana", 1) if e.s.cards[c].defn in ("T702", "T001")) == 2
