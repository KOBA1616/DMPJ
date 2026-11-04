"""語彙パイロット第23弾（2026-10-31）の検証: クリスタルアームズ（水晶武装）。

- op flip_down でマナゾーンのカードを裏向きにできる
- 裏向きのマナは無色扱い: 支払いの文明を満たせない（マナの数としては数える）
- 「水晶武装N」は裏向きマナの枚数を count（filter: face_down）で数える条件で書ける
"""
from conftest import setup


def _answer(e, d, plan):
    keys = [o["key"] for o in d["options"]]
    for kind, want in plan:
        if d["kind"] != kind:
            continue
        for k in keys:
            if k.startswith(want):
                e.answer([keys.index(k)])
                return
    if d["kind"] == "yes_no":
        e.answer([keys.index("yes")] if "yes" in keys else [0])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _flip_pick(e, keys):
    """裏向き化の選択肢（マナ全枚が候補で並びはゾーン順）から、まだ表向きの水マナの位置を返す。"""
    mana = e.zlist("mana", 0)
    if len(keys) != len(mana):
        return None
    for i, c in enumerate(mana):
        if e.s.cards[c].defn == "T003" and not e.s.cards[c].face_down:
            return i
    return None


def _summon_both(e):
    """T063 を2体召喚し、それぞれの ETB で水マナを1枚ずつ裏向きにする。"""
    for _ in range(80):
        tops = [c for c in e.bz_tops(0) if e.s.cards[c].defn == "T063"]
        flipped = [c for c in e.zlist("mana", 0) if e.s.cards[c].face_down]
        if len(tops) >= 2 and len(flipped) >= 2:
            return tops, flipped
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_cards":       # 裏向きにするマナを選ぶ局面
            i = _flip_pick(e, keys)
            if i is not None:
                e.answer([i])
                continue
            e.answer(list(range(d["min"])))
            continue
        _answer(e, d, [("main", "play:T063")])
    raise AssertionError("2体の召喚と裏向き化が完了しなかった")


def test_crystal_arms_cycle(rules):
    e = setup(rules, {"hand": ["T063", "T063"], "mana": ["T003", "T003", "T001", "T001", "T001"]}, {})
    tops, flipped = _summon_both(e)
    assert all(e.s.cards[c].face_down for c in flipped)                 # 裏向きになった
    assert all(e.chars(c)["power"] == 6000 for c in tops)               # 水晶武装2: 2枚以上で +3000


def test_face_down_mana_is_colorless(rules):
    e = setup(rules, {"hand": ["T063", "T003"], "mana": ["T003", "T003", "T001", "T001"]}, {})
    tops, flipped = [], []
    for _ in range(50):
        fd = [c for c in e.zlist("mana", 0) if e.s.cards[c].face_down]
        if fd:
            flipped = fd
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_cards":
            i = _flip_pick(e, keys)
            e.answer([i] if i is not None else list(range(d["min"])))
            continue
        _answer(e, d, [("main", "play:T063")])
    assert flipped, "裏向きにならなかった"
    # 裏向きでない水マナはもう無い（残りは T001 と裏向き T003）ので、水コストの呪文は文明を満たせない
    spell = next(c for c in e.zlist("hand", 0) if e.s.cards[c].defn == "T003")
    assert e._mana_choices(spell, 0) == []
