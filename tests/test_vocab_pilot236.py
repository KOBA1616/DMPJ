"""第236弾: 超無限進化（evolve_any の複数重ね＋evolve_total_cost_ge）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _play_evo(e, defn, picks, max_steps=140):
    """進化クリーチャーを出す。choose_evo_source では picks 体まで1体ずつ選ぶ。"""
    picked = 0
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith(f"play:{defn}") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith(f"play:{defn}"))])
        elif d["kind"] == "choose_evo_source":
            if picked < picks:
                picked += 1
                e.answer([0])
            else:
                e.answer([])          # もう重ねない
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if defn in _defns(e, "bz", 0):
            top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == defn)
            return len(e.s.cards[top].under)
    return None


def _main_options(e, max_steps=10):
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None
        if d["kind"] == "main":
            return [o["key"] for o in d["options"]]
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return []


def test_evolve_any_stacks_three():
    e = setup(_rules(), {"bz": ["T621", "T621", "T621"], "hand": ["T640"],
                         "mana": ["T551"] * 5}, {})
    # evolve_any は1回の提示で複数を選ぶ形: driver は範囲選択に任せるため picks は大きく
    unders = None
    for _ in range(140):
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:T640") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T640"))])
        elif d["kind"] == "choose_evo_source":
            e.answer(list(range(d["max"])))     # 全部重ねる
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if "T640" in _defns(e, "bz", 0):
            top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T640")
            unders = len(e.s.cards[top].under)
            break
    assert unders == 3


def test_total_cost_picks_until_budget():
    # T621（コスト3）×2 = 合計6 ≥ 5: 1体目（3）では確定できず、2体目で確定できる
    e = setup(_rules(), {"bz": ["T621", "T621"], "hand": ["T641"],
                         "mana": ["T551"] * 5}, {})
    unders = _play_evo(e, "T641", picks=99)
    assert unders == 2


def test_total_cost_not_offered_when_pool_short():
    # T621×1 = 合計3 < 5: 出せない
    e = setup(_rules(), {"bz": ["T621"], "hand": ["T641"],
                         "mana": ["T551"] * 5}, {})
    keys = _main_options(e)
    assert not any(k.startswith("play:T641") for k in keys)


def test_mana_number_set_to_zero():
    # 第236弾の前提修正: mod mana_number は 0 への置換も表せる（未設定は None）
    e = setup(_rules(), {"hand": ["T642"], "mana": ["T050"] * 3},
              {"mana": ["T002", "T002"]})
    for _ in range(60):
        if "T642" in _defns(e, "bz", 0):
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:T642") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T642"))])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    # 誘発が解決した時点（相手ターン中）で測る。自分の次のターン開始で失効するのが正しい
    assert all(e.chars_ro(c)["mana_number"] == 0 for c in e.zlist("mana", 1))
    # 自分のマナは通常どおり（未設定 = None）
    assert all(e.chars_ro(c)["mana_number"] is None for c in e.zlist("mana", 0))
