"""第238弾の登録形テスト: lose_protection 再変換（ラウンド274）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["dm25bd1-001", "dm25bd2-003", "dm24ex3-rp3tr1"]


def _game(p0, p1):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                         "deck_size": 20})


def test_all_registered():
    e = _game({}, {})
    for cid in IDS:
        assert cid in e.rules.cards, cid


def test_bd1_no_lose_during_opponent_turn():
    e = _game({"bz": ["dm25bd1-001"]}, {})
    assert e._lose_immune(0, "direct_attack") is False   # 自分のターン中
    for _ in range(40):
        if e.s.active == 1:
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert e.s.active == 1
    assert e._lose_immune(0, "direct_attack") is True    # 相手のターン中は負けない
    assert e._lose_immune(0, "deck_out") is True


def test_rp3tr1_spell_face_grants_deck_out_immunity():
    e = _game({"hand": ["dm24ex3-rp3tr1"], "mana": ["T030"] * 8}, {})
    for _ in range(80):
        if any((ce.get("no_lose") or {}).get("deck_out_only") for ce in e.s.continuous):
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and "play:dm24ex3-rp3tr1:1" in keys:
            e.answer([keys.index("play:dm24ex3-rp3tr1:1")])   # 呪文面
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert any((ce.get("no_lose") or {}).get("deck_out_only") for ce in e.s.continuous)
    assert e._lose_immune(0, "deck_out") is True
    assert e._lose_immune(0, "direct_attack") is False    # 山札切れだけを防ぐ
