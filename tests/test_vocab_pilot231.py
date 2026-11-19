"""第231弾: 進化V（同プール2体）と star＋複数進化元の分離再構築。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _tops(e, p):
    return [c for c in e.zlist("bz", p)
            if e.s.cards[c].controller == p and e.s.cards[c].top_of < 0]


def _play_evo(e, defn, max_steps=140):
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith(f"play:{defn}") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith(f"play:{defn}"))])
        elif d["kind"] in ("pay_mana", "choose_evo_source"):
            e.answer(list(range(d["min"])))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if defn in _defns(e, "bz", 0) and e.s.turn >= 1 and d["kind"] == "attack":
            return
    raise AssertionError("evolution did not complete")


def test_v_same_pool_two_bases():
    e = setup(_rules(), {"bz": ["T621", "T621"], "hand": ["T622"],
                         "mana": ["T551"] * 4}, {})
    _play_evo(e, "T622")
    top = next(c for c in _tops(e, 0) if e.s.cards[c].defn == "T622")
    assert len(e.s.cards[top].under) == 2
    assert len(e.s.cards[top].stack_bases) == 2
    assert {e.s.cards[u].defn for u in e.s.cards[top].under} == {"T621"}


def test_star_v_bases_become_separate():
    e = setup(_rules(), {"bz": ["T624", "T625"], "hand": ["T623"],
                         "mana": ["T551", "T551", "T551", "T002", "T002"]},
              {"bz": ["T397"]})
    _play_evo(e, "T623")
    top = next(c for c in _tops(e, 0) if e.s.cards[c].defn == "T623")
    # P1 のターンに T397 で攻撃して破壊する（T623 をタップ状態にして攻撃対象にする）
    for _ in range(160):
        if "T623" in _defns(e, "graveyard", 0):
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and d["player"] == 1:
            e.s.cards[top].tapped = True
            ak = next((k for k in keys if "T623" in k), None)
            e.answer([keys.index(ak)] if ak else [keys.index("pass")])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "T623" in _defns(e, "graveyard", 0)
    tops = {e.s.cards[c].defn for c in _tops(e, 0)}
    assert "T624" in tops and "T625" in tops      # 下の2枚が別々のクリーチャーとして残る
    for c in _tops(e, 0):
        assert e.s.cards[c].under == [] or e.s.cards[c].defn not in ("T624", "T625")


def test_non_star_v_leaves_as_whole_stack():
    e = setup(_rules(), {"bz": ["T621", "T621"], "hand": ["T622"],
                         "mana": ["T551"] * 4}, {"bz": ["T397"]})
    _play_evo(e, "T622")
    top = next(c for c in _tops(e, 0) if e.s.cards[c].defn == "T622")
    for _ in range(160):
        if "T622" in _defns(e, "graveyard", 0):
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and d["player"] == 1:
            e.s.cards[top].tapped = True
            ak = next((k for k in keys if "T622" in k), None)
            e.answer([keys.index(ak)] if ak else [keys.index("pass")])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "T622" in _defns(e, "graveyard", 0)
    assert _defns(e, "graveyard", 0).count("T621") == 2   # 束ごと墓地へ
    assert "T621" not in {e.s.cards[c].defn for c in _tops(e, 0)}
