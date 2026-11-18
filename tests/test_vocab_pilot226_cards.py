"""第226弾の登録形テスト: cast_from_graveyard 再変換4枚＋別刷り折り畳み1件（ラウンド262）。

converted.yaml の実カードで確認する。dm26ex4-sec022 は dm26ex4-011 の
別刷りとして submit が自動で aliases に折り畳んだことも確認する。
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["dm26ex2-mc004", "dmex18-s06", "dmrp03-004", "dm26ex4-011"]


def _game(p0, p1):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                         "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _run(e, play=None, pick=None, mode=None, stop_when=None, max_steps=400):
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        if stop_when is not None and stop_when(e):
            return d
        keys = _keys(d)
        kind = d["kind"]
        if kind == "main" and play:
            pk = next((k for k in keys if k.startswith(play)), None)
            if pk is not None:
                e.answer([keys.index(pk)])
                continue
        if kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "choose_mode" and mode is not None:
            e.answer([mode])
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


def test_all_registered_and_alias_folded():
    e = _game({}, {})
    for cid in IDS:
        assert cid in e.rules.cards, cid
    c011 = e.rules.cards["dm26ex4-011"]
    assert "dm26ex4-sec022" in (c011.source.get("aliases") or [])
    rows = [json.loads(l) for l in open("data/cards/raw/rejects.jsonl")]
    assert all(r["id"] != "dm26ex4-sec022" for r in rows)


def test_mc004_grave_cast_modal():
    e = _game({"graveyard": ["dm26ex2-mc004"],
               "mana": ["T050", "T050", "T050", "T001", "T001"]},
              {"hand": ["T001", "T002", "T006"]})
    _run(e, play="play:dm26ex2-mc004:grave", mode=0,
         stop_when=lambda e: len(_defns(e, "graveyard", 1)) == 2)
    assert len(_defns(e, "graveyard", 1)) == 2       # モード1を2回: 相手は2枚捨てる
    assert _defns(e, "deck", 0)[-1] == "dm26ex2-mc004"   # 唱えた後は山札の下


def test_dmrp03_004_grant_and_cast_draw():
    e = _game({"bz": ["dmrp03-004"], "graveyard": ["T003"],
               "mana": ["T030", "T001"]}, {})
    _run(e, play="play:T003:grave",
         stop_when=lambda e: len(_defns(e, "hand", 0)) == 3)
    assert len(_defns(e, "hand", 0)) == 3            # T003 の2枚＋唱えた時ドロー
    assert _defns(e, "deck", 0)[-1] == "T003"


def test_011_graveyard_cost_reduction_applies():
    e = _game({"bz": ["dm26ex4-011"], "graveyard": ["T003"], "mana": ["T030"]}, {})
    _run(e, play="play:T003:grave",
         stop_when=lambda e: _defns(e, "deck", 0)[-1] == "T003")
    assert _defns(e, "deck", 0)[-1] == "T003"        # 墓地コスト-2（下限1）で1マナで唱えられた


def test_s06_recast():
    e = _game({"bz": ["dmex18-s06"], "hand": ["T003"], "mana": ["T030", "T001"]}, {})
    _run(e, play="play:T003",
         stop_when=lambda e: len(_defns(e, "hand", 0)) >= 4)
    assert len(_defns(e, "hand", 0)) == 4            # 2枚引く×2回（再演）
    assert "T003" in _defns(e, "graveyard", 0)


def test_s06_not_chosen_by_opponent_spells():
    # 相手の呪文（T006: パワー4000以下を破壊）では選べない。
    # 候補が T002 だけなら選択は自動解決される（決定が出たら s06 が含まれないことも確認）。
    e = _game({"bz": ["dmex18-s06", "T002"]}, {"hand": ["T006"],
              "mana": ["T551", "T551", "T551"]})
    for _ in range(200):
        if "T002" in _defns(e, "graveyard", 0):
            break
        d = e.advance()
        assert d is not None
        keys = _keys(d)
        if d["kind"] == "main" and d["player"] == 1:
            pk = next((k for k in keys if k.startswith("play:T006")), None)
            if pk is not None:
                e.answer([keys.index(pk)])
                continue
        if d["kind"] == "choose_cards" and d["player"] == 1:
            assert not any("dmex18-s06" in k for k in keys)   # 相手の呪文には選ばれない
            e.answer([next(i for i, k in enumerate(keys) if "T002" in k)])
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "T002" in _defns(e, "graveyard", 0)       # T002 は破壊された
    assert "dmex18-s06" in _defns(e, "bz", 0)        # s06（パワー4000）には触れられない
