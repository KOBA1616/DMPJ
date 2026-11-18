"""語彙パイロット第218弾: 超無限進化 chou_mugen_evolution（単独9件）。

既存の evolve_any（1体以上の進化元、超無限墓地進化・G-NEO で使用）に不足していた3点を足す:
- 文明条件 evolve_civs: 選んだ進化元の集合が指定文明を全て含むこと（1体ずつ選び、揃うまで終われない）
- 超無限進化Ω evolve_zones: 進化元を複数ゾーン（墓地・マナ・バトルゾーン）から探す
- ソウルシフト∞ soul_shift {floor}: 実際に重ねた進化元の合計コストぶん軽減し、floor 未満にはならない

proto: T559（素の超無限進化）/ T560（文明条件）/ T561（Ω）/ T562（ソウルシフト∞、floor 0）
"""
from conftest import setup


def _settle(e, done, drive=None, max_steps=400):
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if drive and drive(e, d, keys):
            continue
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    return done()


def _driver(play_key, evo_plan=None):
    """play_key を出し、choose_evo_source は evo_plan（cid の集合 or 逐次プラン関数）に従う。"""
    st = {"played": False}

    def drive(e, d, keys):
        if d["kind"] == "main" and d["player"] == 0 and not st["played"]:
            if play_key in keys:
                st["played"] = True
                e.answer([keys.index(play_key)])
                return True
        if d["kind"] == "choose_evo_source" and d["player"] == 0:
            e.answer(evo_plan(e, d))
            return True
        if d["kind"] == "pay_mana" and d["player"] == 0:
            e.answer([0])
            return True
        return False

    return st, drive


def _pick(cids):
    def plan(e, d):
        want = [i for i, o in enumerate(d["options"]) if o["cid"] in cids]
        return want[: max(d["min"], len(want))]
    return plan


def test_parse(rules):
    from dmsim.cards.defs import parse_card, load_tables
    from tests._conv_cache import proto_card
    tables = load_tables()
    fs = {cid: parse_card(proto_card(cid), tables) for cid in ("T559", "T560", "T561", "T562")}
    assert fs["T560"].evolve_civs == ("light", "water", "fire")
    assert fs["T561"].evolve_zones == ("graveyard", "mana", "bz")
    assert fs["T562"].soul_shift == {"floor": 0}


def test_mugen_stacks_two_dragons(rules):
    e = setup(rules, {"hand": ["T559"], "bz": ["T063", "T064"],
                      "mana": ["T556"] + ["T001"] * 7}, {})
    top = e.zlist("hand", 0)[0]
    bases = set(e.zlist("bz", 0))
    st, drive = _driver("play:T559", _pick(bases))
    ok = _settle(e, lambda: e.s.cards[top].zone == "bz" and len(e.s.cards[top].under) == 2, drive)
    assert ok and st["played"]
    assert set(e.s.cards[top].under) == bases
    assert all(e.s.cards[b].zone == "bz" for b in bases)


def test_mugen_single_base_ok(rules):
    e = setup(rules, {"hand": ["T559"], "bz": ["T063"],
                      "mana": ["T556"] + ["T001"] * 7}, {})
    top = e.zlist("hand", 0)[0]
    base = e.zlist("bz", 0)[0]
    st, drive = _driver("play:T559", _pick({base}))
    assert _settle(e, lambda: e.s.cards[top].zone == "bz", drive)
    assert e.s.cards[top].under == [base]


def test_civ_cover_needs_all_civs(rules):
    # 光と水しかいないと、そもそも出す選択肢が出ない
    e = setup(rules, {"hand": ["T560"], "bz": ["T004", "T063"],
                      "mana": ["T004"] + ["T001"] * 6}, {})
    seen = {}

    def drive(e, d, keys):
        if d["kind"] == "main" and d["player"] == 0:
            seen["playable"] = "play:T560" in keys
            return True
        return False

    _settle(e, lambda: "playable" in seen, drive, 60)
    assert seen["playable"] is False


def test_civ_cover_incremental_selection(rules):
    e = setup(rules, {"hand": ["T560"], "bz": ["T004", "T063", "T064"],
                      "mana": ["T004"] + ["T001"] * 6}, {})
    top = e.zlist("hand", 0)[0]
    bases = {c: e.s.cards[c].defn for c in e.zlist("bz", 0)}
    mins = []

    def plan(e, d):
        mins.append(d["min"])
        # まだ選んでいない文明のカードを1体ずつ選ぶ。全文明が揃ったら止める（空回答）
        picked = plan.picked
        have = {e.chars(c)["civs"][0] for c in picked}
        if {"light", "water", "fire"} <= have:
            return []
        for i, o in enumerate(d["options"]):
            civ = e.chars(o["cid"])["civs"][0]
            if civ not in have:
                picked.append(o["cid"])
                return [i]
        return []

    plan.picked = []
    st, drive = _driver("play:T560", plan)
    ok = _settle(e, lambda: e.s.cards[top].zone == "bz" and len(e.s.cards[top].under) == 3, drive)
    assert ok
    assert set(e.s.cards[top].under) == set(bases)
    assert mins[0] == 1 and mins[1] == 1     # 揃うまでは min=1（止まれない）


def test_omega_sources_from_three_zones(rules):
    e = setup(rules, {"hand": ["T561"], "bz": ["T004"], "graveyard": ["T001"],
                      "mana": ["T008", "T065"] + ["T001"] * 5}, {})
    top = e.zlist("hand", 0)[0]
    srcs = {e.zlist("bz", 0)[0], e.zlist("graveyard", 0)[0],
            next(c for c in e.zlist("mana", 0) if e.s.cards[c].defn == "T065")}
    st, drive = _driver("play:T561", _pick(srcs))
    ok = _settle(e, lambda: e.s.cards[top].zone == "bz" and len(e.s.cards[top].under) == 3, drive)
    assert ok
    assert set(e.s.cards[top].under) == srcs
    assert all(e.s.cards[b].zone == "bz" for b in srcs)   # 墓地・マナの進化元も下のカードとして場へ


def test_soul_shift_reduces_by_source_costs(rules):
    # T063（コスト3）+ T064（コスト4）を重ねる → 10 - 7 = 3 マナだけ払う
    e = setup(rules, {"hand": ["T562"], "bz": ["T063", "T064"], "mana": ["T001"] * 5}, {})
    top = e.zlist("hand", 0)[0]
    bases = set(e.zlist("bz", 0))
    st, drive = _driver("play:T562", _pick(bases))
    ok = _settle(e, lambda: e.s.cards[top].zone == "bz", drive)
    assert ok
    tapped = sum(1 for c in e.zlist("mana", 0) if e.s.cards[c].tapped)
    assert tapped == 3


def test_soul_shift_floor_zero(rules):
    # 合計コスト 3+4+3 = 10 → 軽減で 0。無色なので 0 マナのまま召喚できる
    e = setup(rules, {"hand": ["T562"], "bz": ["T063", "T064", "T065"], "mana": ["T001"] * 2}, {})
    top = e.zlist("hand", 0)[0]
    bases = set(e.zlist("bz", 0))
    st, drive = _driver("play:T562", _pick(bases))
    ok = _settle(e, lambda: e.s.cards[top].zone == "bz" and len(e.s.cards[top].under) == 3, drive)
    assert ok
    tapped = sum(1 for c in e.zlist("mana", 0) if e.s.cards[c].tapped)
    assert tapped == 0
