"""第228弾の登録形テスト: crystal_charger 再変換5枚（ラウンド264）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["dm23ex3-015", "dm24bd6-007", "dm24bd6-033", "dm24bd6-036", "dm26rp2-t001"]


def _game(p0, p1):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                         "deck_size": 20})


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _answer(e, d, play=None, pick=None):
    keys = [o["key"] for o in d["options"]]
    if d["kind"] == "main" and play:
        pk = next((k for k in keys if play in k), None)
        if pk is not None:
            e.answer([keys.index(pk)])
            return
    if d["kind"] == "pay_mana":
        e.answer(list(range(d["min"])))
    elif d["kind"] == "choose_cards" and pick:
        idx = next((i for i, k in enumerate(keys) if pick in k), None)
        e.answer([idx] if idx is not None else list(range(d["min"])))
    elif d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def test_all_registered():
    e = _game({}, {})
    for cid in IDS:
        assert cid in e.rules.cards, cid


def test_t001_spell_face_judge_and_charger():
    e = _game({"hand": ["dm26rp2-t001"], "mana": ["T030", "T030", "T001"]},
              {"bz": ["T201", "T002"], "mana": ["T001", "T002"]})
    # 呪文面（面1）を唱える: 相手マナ2枚より大きいコストの T201 を山札の下へ
    for _ in range(120):
        if _defns(e, "deck", 1) and _defns(e, "deck", 1)[-1] == "T201":
            break
        d = e.advance()
        assert d is not None
        _answer(e, d, play="play:dm26rp2-t001:1", pick="T201")
    assert _defns(e, "deck", 1)[-1] == "T201"
    assert "T002" in _defns(e, "bz", 1)          # コスト2は対象外（マナ2枚より大きくない）
    # 唱えた呪文面は裏向きで自分のマナへ
    mana0 = [c for c in e.zlist("mana", 0) if e.s.cards[c].defn == "dm26rp2-t001"]
    assert len(mana0) == 1 and e.s.cards[mana0[0]].face_down is True


def test_t001_creature_face_attack_lock():
    e = _game({"bz": ["dm26rp2-t001"]},
              {"hand": ["T542"], "mana": ["T551", "T551", "T551"]})
    first_attack_turn = None
    for _ in range(160):
        d = e.advance()
        assert d is not None
        if d["kind"] == "attack" and d["player"] == 1:
            first_attack_turn = e.s.turn
            keys = [o["key"] for o in d["options"]]
            e.answer([keys.index("pass")])
            break
        _answer(e, d, play="play:T542")
    assert "T542" in _defns(e, "bz", 1)
    # 出たターン（相手の1ターン目=turn 2）には攻撃決定自体が出ず、次の自分のターンで初めて攻撃できる
    assert first_attack_turn is not None and first_attack_turn >= 4


def test_015_spell_face_bounce_and_charger():
    e = _game({"hand": ["dm23ex3-015"], "mana": ["T030", "T030", "T001"]},
              {"bz": ["T002", "T201"]})
    for _ in range(120):
        if "T002" in _defns(e, "hand", 1):
            break
        d = e.advance()
        assert d is not None
        _answer(e, d, play="play:dm23ex3-015:1", pick="T002")
    assert "T002" in _defns(e, "hand", 1)         # コスト2以下をバウンス
    assert "T201" in _defns(e, "bz", 1)
    mana0 = [c for c in e.zlist("mana", 0) if e.s.cards[c].defn == "dm23ex3-015"]
    assert len(mana0) == 1 and e.s.cards[mana0[0]].face_down is True
