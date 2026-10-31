"""語彙パイロット第19弾（2026-10-31）の検証。

ハイパーモード（rejects: hyper_mode）: 面に hyper: true を宣言する。
- メインステップで「ハイパー化」の選択肢が出て、自分の他のクリーチャーを1体タップすると解放される
- ハイパーモードの間だけ、条件 {hyper: true} の能力が働く
- 次の自分のターンのはじめに解ける
"""
from conftest import setup


def _find_main(e, key, turns=6):
    for _ in range(40):
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d["player"] == 0 and key in keys:
            return d, keys
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError(f"選択肢 {key} が出なかった")


def test_hyper_mode_cycle(rules):
    e = setup(rules, {"hand": ["T059"], "bz": ["T001", "T003"], "mana": ["T005"] * 3}, {})
    _find_main(e, "play:T059")
    e.answer([[o["key"] for o in e.s.waiting["options"]].index("play:T059")])
    dog = None
    for _ in range(15):
        tops = [c for c in e.bz_tops(0) if e.s.cards[c].defn == "T059"]
        if tops:
            dog = tops[0]
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert dog is not None and not e.s.cards[dog].hyper
    # メインステップでハイパー化する（他のクリーチャーをタップする）
    d, keys = _find_main(e, "hyper:T059")
    e.answer([keys.index("hyper:T059")])
    for _ in range(10):
        d = e.advance()
        if d is None or e.s.cards[dog].hyper:
            break
        keys = [o["key"] for o in d["options"]]
        e.answer(list(range(d["min"])))
    assert e.s.cards[dog].hyper
    tapped_allies = [c for c in e.bz_tops(0) if c != dog and e.s.cards[c].tapped]
    assert tapped_allies                              # 解放のコストとして味方がタップされた
    # ハイパーモードの間は攻撃時に引ける。ターンが進んで自分のターンのはじめに解ける
    hand_before = len(e.zlist("hand", 0))
    drew = False
    released = False
    turn_seen = e.s.turn
    for _ in range(80):
        d = e.advance()
        if d is None:
            break
        if e.s.turn > turn_seen and e.s.active == 0:
            released = not e.s.cards[dog].hyper      # 自分のターンのはじめに解けた
            break
        keys = [o["key"] for o in d["options"]]
        atk = [k for k in keys if k == "attack:T059:player"]
        if d["kind"] == "attack" and atk:
            e.answer([keys.index(atk[0])])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if len(e.zlist("hand", 0)) > hand_before:
            drew = True
    assert drew                                       # ハイパーモード中の攻撃で引けた
    assert released                                   # 次の自分のターンのはじめに解けた
