"""第247弾の登録形: dmx21-045 アクテリオン・フォース（ラウンド281）。"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build


def test_registered_strigger_x():
    rules = load_rules()
    assert "dmx21-045" in rules.cards
    card = rules.cards["dmx21-045"]
    assert "dm15-s05" in (card.source or {}).get("aliases", [])
    e = build(rules, {"p0": {"bz": ["T002"], "shield": ["dmx21-045"]},
                      "p1": {"bz": ["T534"]}, "filler": "T001", "seed": 1, "deck_size": 20})
    gear = next(c for c in e.zlist("shield", 0) if e.s.cards[c].defn == "dmx21-045")
    host = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T002")
    for _ in range(300):
        if e.s.cards[gear].crossed:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        atk = next((i for i, k in enumerate(keys) if k.startswith("attack:")), None)
        if atk is not None:
            e.answer([atk])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert gear in e.zlist("bz", 0)
    assert e.s.cards[gear].crossed == e.s.ref(host)
    assert "triple_breaker" in e.chars_ro(host)["keywords"]
