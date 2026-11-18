"""語彙パイロット第226弾: cast_from_graveyard（墓地から通常コストで唱える）。

面項目 grave_cast（自身型）と許可型 allow [cast_from_graveyard]（ターン1回）。
解決後は山札の一番下。proto T599-T601（T601 は再演型の検証）。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests._conv_cache import proto_card as _proto_card
from tests.conftest import setup


def test_proto_parse():
    assert _proto_card("T599")["grave_cast"] is True
    t600 = _proto_card("T600")
    assert t600["abilities"][0]["mod"] == {"allow": [{"action": "cast_from_graveyard", "once": True}]}
    _proto_card("T601")


def _keys(d):
    return [o["key"] for o in d["options"]]


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _run(e, play=None, stop_when=None, main_keys=None, max_steps=400):
    """単一ドライバ。main_keys を渡すと、最後に止まったメイン決定のキーを集める。"""
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        if stop_when is not None and stop_when(e):
            return d
        keys = _keys(d)
        kind = d["kind"]
        if kind == "main" and main_keys is not None:
            main_keys.extend(keys)
        if kind == "main" and play:
            pk = next((k for k in keys if k.startswith(play)), None)
            if pk is not None:
                e.answer([keys.index(pk)])
                continue
        if kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "choose_cards":
            e.answer(list(range(d["min"])))
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


def test_599_self_grave_cast(rules):
    e = setup(rules, {"graveyard": ["T599"], "mana": ["T050", "T050", "T050"]}, {},
              filler="T001", seed=1)
    _run(e, play="play:T599:grave",
         stop_when=lambda e: len(_defns(e, "hand", 0)) == 1)
    assert len(_defns(e, "hand", 0)) == 1            # 唱えて1枚引く
    assert _defns(e, "graveyard", 0) == []           # 墓地には戻らない
    assert _defns(e, "deck", 0)[-1] == "T599"        # 山札の一番下へ


def test_600_grant_once_per_turn(rules):
    e = setup(rules, {"bz": ["T600"], "graveyard": ["T003", "T006"],
                      "mana": ["T030", "T551", "T001", "T001", "T001"]}, {},
              filler="T001", seed=1)
    _run(e, play="play:T003:grave",
         stop_when=lambda e: len(_defns(e, "hand", 0)) == 3)
    assert _defns(e, "deck", 0)[-1] == "T003"        # 唱えた後は山札の下
    assert len(_defns(e, "hand", 0)) == 3            # T003 の2枚＋唱えた時ドロー1枚
    # 次の自分のターン（ターン3）のメインでは、ターン1回が回復して再び提示される
    keys = []
    for _ in range(200):
        d = e.advance()
        assert d is not None
        ks = _keys(d)
        if d["kind"] == "main" and d["player"] == 0 and e.s.turn >= 3:
            keys = ks
            break
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "block":
            e.answer([ks.index("no_block")])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif d["kind"].startswith("declare"):
            e.answer([])
        elif "pass" in ks:
            e.answer([ks.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert any(k.startswith("play:T006:grave") for k in keys), keys


def test_601_recast_from_graveyard(rules):
    e = setup(rules, {"bz": ["T601"], "hand": ["T003"], "mana": ["T030", "T001"]}, {},
              filler="T001", seed=1)
    _run(e, play="play:T003",
         stop_when=lambda e: len(_defns(e, "hand", 0)) >= 4)
    assert len(_defns(e, "hand", 0)) == 4            # 2枚引く×2回（再演が効いた）
    assert "T003" in _defns(e, "graveyard", 0)       # 再演後は通常どおり墓地へ


def test_601_no_recast_for_graveyard_casts(rules):
    # 墓地から唱えた呪文では再演しない（「手札から唱えた時」限定。再演自体のループも防ぐ）
    e = setup(rules, {"bz": ["T601"], "graveyard": ["T599"],
                      "mana": ["T050", "T050", "T050"]}, {},
              filler="T001", seed=1)
    _run(e, play="play:T599:grave",
         stop_when=lambda e: len(_defns(e, "hand", 0)) == 1)
    assert len(_defns(e, "hand", 0)) == 1            # T599 自身のドロー1枚だけ
    assert _defns(e, "deck", 0)[-1] == "T599"
