"""語彙パイロット第15弾（2026-10-31）の検証。

ギャラクシールド（rejects: galaxyshield）:
- 面の galaxy_shield {cost, civs} で代替コストを宣言する。メインステップに
  「:gshield」の選択肢が出て、払うと召喚ではなく表向きでシールド化する
- 置かれた時の誘発は when の face_up: true で「表向きで置かれた時」に絞れる
- 自分のターンのはじめ、表向きでシールドゾーンにあれば op summon_self で
  「コストを支払ったものとして」召喚する（支払いはしないが unpaid にならない）
"""
from conftest import setup


def test_galaxyshield_place_and_summon(rules):
    e = setup(rules, {"hand": ["T052"], "mana": ["T004", "T003"] * 3}, {})
    cid = next(c for c in e.zlist("hand", 0) if e.s.cards[c].defn == "T052")
    hand0 = len(e.zlist("hand", 0))
    placed = False
    for _ in range(30):   # 1ターン目: 代替コストでシールド化し、置いた時誘発（3ドロー）まで
        if e.s.cards[cid].zone == "shield" and len(e.zlist("hand", 0)) >= hand0 + 2:
            placed = True
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and "play:T052:gshield" in keys:
            e.answer([keys.index("play:T052:gshield")])
        elif d["kind"] == "yes_no":
            e.answer([keys.index("yes")])          # 引く
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert placed
    assert e.s.cards[cid].face_up is True           # 表向きで置かれた
    # 2ターン目のはじめに召喚される
    summoned = False
    for _ in range(40):
        if e.s.cards[cid].zone == "bz":
            summoned = True
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert summoned
