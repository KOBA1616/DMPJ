"""第230弾の登録形テスト: leave_protection_vs_opponent_spells 再変換5枚（ラウンド266）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["promoy6-003", "dm22rp1-004", "dmr03-010", "dmx22a-029", "dm33-012"]


def _game(p0, p1):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                         "deck_size": 20})


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _opp_destroy(e, target, max_steps=120):
    for _ in range(max_steps):
        if "T006" in _defns(e, "graveyard", 1):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:T006") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T006"))])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "choose_cards":
            pk = next((i for i, k in enumerate(keys) if target in k), None)
            e.answer([pk] if pk is not None else list(range(d["min"])))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("spell did not resolve")


def _settle(e, steps=8):
    for _ in range(steps):
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


def test_all_registered():
    e = _game({}, {})
    for cid in IDS:
        assert cid in e.rules.cards, cid


def test_029_self_protected():
    e = _game({"bz": ["dmx22a-029"]},
              {"hand": ["T006"], "mana": ["T551", "T551", "T551"]})
    _opp_destroy(e, "dmx22a-029")
    _settle(e)
    assert "dmx22a-029" in _defns(e, "bz", 0)
    assert "dmx22a-029" not in _defns(e, "graveyard", 0)


def test_rp004_protects_abyss_ally():
    e = _game({"bz": ["dm22rp1-004", "T619"]},
              {"hand": ["T006"], "mana": ["T551", "T551", "T551"]})
    _opp_destroy(e, "T619")
    _settle(e)
    assert "T619" in _defns(e, "bz", 0)          # 自分のアビスは相手の呪文では離れない
