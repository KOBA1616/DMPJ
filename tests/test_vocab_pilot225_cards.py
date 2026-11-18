"""第225弾の登録形テスト: cross_gear_mechanic 再変換4枚（ラウンド261）。

converted.yaml の実カードで確認する。差し戻し2件（dmx21-045 → strigger_x、
promoy4-002 → cross_cost_reduction）は rejects に残ることも確認する。
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["dmx21-047", "dmx21-046", "dmx21-013", "dmx12b-025"]


def _game(p0, p1):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                         "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _cid(e, p, defn, zone="bz"):
    return next(c for c in e.zlist(zone, p) if e.s.cards[c].defn == defn)


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _run(e, play=None, pick=None, attack=None, stop_when=None, cross=None,
         max_steps=400):
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        if stop_when is not None and stop_when(e):
            return
        keys = _keys(d)
        kind = d["kind"]
        if kind == "main" and play:
            pk = next((k for k in keys if k.startswith(play)), None)
            if pk is not None:
                e.answer([keys.index(pk)])
                continue
        if kind == "main" and cross and cross in keys:
            e.answer([keys.index(cross)])
            continue
        if kind == "attack" and attack and f"attack:{attack}:player" in keys:
            e.answer([keys.index(f"attack:{attack}:player")])
            continue
        if kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "choose_cards":
            idx = next((i for i, k in enumerate(keys) if pick and pick in k), None)
            e.answer([idx] if idx is not None else list(range(d["min"])))
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif kind == "choose_shields":
            e.answer(list(range(d["min"])))
        elif kind == "yes_no":
            e.answer([0])
        elif kind.startswith("declare"):
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("did not settle")


def test_all_registered_and_bounced():
    e = _game({}, {})
    for cid in IDS:
        assert cid in e.rules.cards, cid
    rows = [json.loads(l) for l in open("data/cards/raw/rejects.jsonl")]
    gaps = {r["id"]: r.get("gaps") for r in rows}
    assert gaps.get("dmx21-045") == ["strigger_x"]
    assert gaps.get("promoy4-002") == ["cross_cost_reduction"]


def test_047_host_plus_and_mana_cycle():
    e = _game({"bz": ["T002", "dmx21-047"]}, {})
    e.s.cards[_cid(e, 0, "dmx21-047")].crossed = e.s.ref(_cid(e, 0, "T002"))
    assert e.chars(_cid(e, 0, "T002"))["power"] == 4000
    _run(e, attack="T002",
         stop_when=lambda e: len(_defns(e, "mana", 0)) == 1
         and len(_defns(e, "hand", 0)) == 1)
    assert len(_defns(e, "mana", 0)) == 1
    assert len(_defns(e, "hand", 0)) == 1


def test_046_spell_puts_from_mana():
    e = _game({"bz": ["T002"], "hand": ["dmx21-046"],
               "mana": ["T551", "T597", "T587"] + ["T001"] * 7}, {})
    _run(e, play="play:dmx21-046",
         stop_when=lambda e: "T597" in _defns(e, "bz", 0))
    bz = _defns(e, "bz", 0)
    assert "T597" in bz and "T587" in bz
    assert "T002" in _defns(e, "mana", 0)


def test_013_reduction_and_restricted_cross():
    e = _game({"bz": ["dmx21-013", "T596"], "hand": ["T598"],
               "mana": ["T030", "T001", "T001", "T001"]}, {})
    _run(e, play="play:T598", cross="cross:dmx21-013:T596:free",
         stop_when=lambda e: "T598" in _defns(e, "bz", 0)
         and e.s.cards[_cid(e, 0, "dmx21-013")].crossed is not None)
    assert "T598" in _defns(e, "bz", 0)              # 軽減で4マナで出た
    ch = e.chars(_cid(e, 0, "T596"))
    assert ch["power"] == 5000 and ch["breaks"] == 2  # 名前制限付きフリー・クロス＋ホスト付与


def test_025_cip_cross_break_trigger():
    e = _game({"bz": ["T002"], "hand": ["dmx12b-025"],
               "mana": ["T030", "T551", "T001", "T001"]},
              {"bz": ["T587", "T060"]})
    _run(e, play="play:dmx12b-025", pick="T587", attack="T002",
         cross="cross:dmx12b-025:T002:free",
         stop_when=lambda e: "T060" in _defns(e, "graveyard", 1)
         and len(_defns(e, "hand", 0)) == 1)
    assert "T587" in _defns(e, "graveyard", 1)       # CIP でギアを墓地へ
    assert "T060" in _defns(e, "graveyard", 1)       # ブレイク誘発で破壊
    assert len(_defns(e, "hand", 0)) == 1            # その後1枚引く
