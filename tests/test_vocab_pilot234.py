"""第234弾: 進化元依存のコスト軽減（evo_base_reduce 面項目／evo_reduce 付与）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _play(e, defn, max_steps=120):
    """defn を出し、支払いでタップしたマナの数を返す（出せなければ None）。
    進化元・支払いの選択肢が1つだけなら決定は自動解決されるので、タップ数で測る。"""
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith(f"play:{defn}") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith(f"play:{defn}"))])
        elif d["kind"] in ("choose_evo_source", "pay_mana"):
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if defn in _defns(e, "bz", 0):
            return sum(1 for c in e.zlist("mana", 0) if e.s.cards[c].tapped)
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


def test_self_form_tamaseed_base_reduces():
    # コスト6 → タマシード進化元なら4で払える（マナは4枚だけ用意）
    e = setup(_rules(), {"bz": ["T633"], "hand": ["T634"],
                         "mana": ["T002"] * 4}, {})
    paid = _play(e, "T634")
    assert paid == 4
    assert "T634" in _defns(e, "bz", 0)


def test_self_form_creature_base_full_price():
    # クリーチャー進化元では軽減なし: マナ4枚では出せない
    e = setup(_rules(), {"bz": ["T621"], "hand": ["T634"],
                         "mana": ["T002"] * 4}, {})
    # T621 は種族テストだが creature なので evolve_from には合う（タマシードではない）
    keys = _main_options(e)
    assert not any(k.startswith("play:T634") for k in keys)


def test_grant_form_reduces_with_floor():
    # コスト5 → 付与で2軽減 = 3（マナ3枚で払える）
    e = setup(_rules(), {"bz": ["T635"], "hand": ["T636"],
                         "mana": ["T002"] * 3}, {})
    paid = _play(e, "T636")
    assert paid == 3
    assert "T636" in _defns(e, "bz", 0)


def test_grant_form_not_offered_below_floor():
    # マナ2枚では床（3）にも届かないので出せない
    e = setup(_rules(), {"bz": ["T635"], "hand": ["T636"],
                         "mana": ["T002"] * 2}, {})
    keys = _main_options(e)
    assert not any(k.startswith("play:T636") for k in keys)
