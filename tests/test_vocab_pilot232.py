"""第232弾: evolve_base_any（どんな種族の進化クリーチャーも置ける進化元）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _drive_to_main(e, want_key, max_steps=60):
    """want_key（play:/cross: で始まるキー）が main 選択肢に出るまで進める。出なければ None。"""
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main":
            if any(k.startswith(want_key) for k in keys):
                return d, keys
            e.answer([keys.index("pass")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return None, None


def _finish_play(e, max_steps=80):
    for _ in range(max_steps):
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        if d["kind"] in ("pay_mana", "choose_evo_source"):
            e.answer(list(range(d["min"])))
        elif d["kind"] == "main":
            return
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


def test_any_race_base_accepts_dragon_evolution():
    e = setup(_rules(), {"bz": ["T626"], "hand": ["T627"],
                         "mana": ["T551"] * 4}, {})
    d, keys = _drive_to_main(e, "play:T627")
    assert d is not None
    e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T627"))])
    _finish_play(e)
    assert "T627" in _defns(e, "bz", 0)
    top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T627")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T626"]


def test_plain_base_rejected():
    e = setup(_rules(), {"bz": ["T619"], "hand": ["T627"],
                         "mana": ["T551"] * 4}, {})
    d, keys = _drive_to_main(e, "play:T627", max_steps=10)
    assert d is None            # 許可のない進化元には置けない


def test_civ_filter_not_faked():
    e = setup(_rules(), {"bz": ["T626"], "hand": ["T629"],
                         "mana": ["T002", "T002", "T002"]}, {})
    d, keys = _drive_to_main(e, "play:T629", max_steps=10)
    assert d is None            # 文明指定は種族許可で肩代わりできない


def test_cross_gear_grants_host():
    e = setup(_rules(), {"bz": ["T619"], "hand": ["T628", "T627"],
                         "mana": ["T551"] * 4 + ["T030"] * 4}, {})
    # まず T628 をジェネレートして T619 にクロスする
    for _ in range(80):
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:T628") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T628"))])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "main" and any(k.startswith("cross:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("cross:"))])
            break
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    d, keys = _drive_to_main(e, "play:T627")
    assert d is not None
    e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T627"))])
    _finish_play(e)
    assert "T627" in _defns(e, "bz", 0)
    top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T627")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T619"]
