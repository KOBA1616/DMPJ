"""第255弾の登録形: breaks_scaling 3件（ラウンド289）。"""
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
    for cid in ("promoy10-007", "dmr12-013", "dm25-s03"):
        parse_card(copy.deepcopy(_converted(cid)), TABLES)
    assert _converted("promoy10-007")["abilities"][1]["mod"]["breaks_add"]["amount"] == 1
    assert _converted("dmr12-013")["abilities"][0]["mod"]["breaks_add"]["amount"] == 1


def test_registered_kurotora_breaks_three():
    rules = load_rules()
    e = build(rules, {"p0": {"bz": ["promoy10-007", "T007", "T007"]},
                      "p1": {"deck": ["T001"] * 12},
                      "filler": "T001", "seed": 1, "deck_size": 16})
    sh1 = len(e.zlist("shield", 1))
    for _ in range(500):
        if len(e.zlist("shield", 1)) <= sh1 - 3:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_breaker":
            e.answer([len(keys) - 1])   # 最大のブレイク数（1 + 他の自然2体 = 3）を選ぶ
        else:
            a = next((i for i, k in enumerate(keys)
                      if k.startswith("attack:promoy10-007") or (k.startswith("attack:") and k.endswith(":player"))), None)
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
    assert len(e.zlist("shield", 1)) == sh1 - 3
