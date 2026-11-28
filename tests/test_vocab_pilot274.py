"""語彙パイロット第274弾: クラシック・ソウルシフト（単体進化）。

第218弾の soul_shift {floor} はソウルシフト∞（超無限進化: 重ねた進化元全員の
コスト合計ぶん軽減）として実装された。クラシックなソウルシフトは通常の単体
進化に付き、軽減は「選んだ進化元1体のコスト」ぶん。支払い側（h_play）は実際に
重ねた進化元の合計で計算するため単体進化では既に正しいが、実現可能性側
（_can_play_face）は候補全体の合計で見積もっており、単体進化では払えない額を
提示してしまう。本弾はその見積もりを「重ねる数ぶんを大きい順」に直し、
クラシック形を soul_shift {floor} で表せることをプロトで証明する。
- floor の対応: 「1より少なくならない」→ {floor: 1}、「0以下にならない」→ {floor: 0}

proto: T770（floor 1, コスト7）/ T771（floor 0, コスト5, 水）/
T772（進化元コスト5）/ T773（進化元コスト3）/ T774（進化元コスト9）/
T775（floor 0, コスト5, 無色）
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


def _tapped_mana(e):
    return [c for c in e.zlist("mana", 0) if e.s.cards[c].tapped]


def _by_defn(e, zone, defn, player=0):
    return [c for c in e.zlist(zone, player) if e.s.cards[c].defn == defn]


def test_parse_classic_soulshift(rules):
    from dmsim.cards.defs import DefError, load_tables, parse_card
    from tests._conv_cache import proto_card
    tables = load_tables()
    f770 = parse_card(proto_card("T770"), tables)
    f771 = parse_card(proto_card("T771"), tables)
    assert f770.soul_shift == {"floor": 1}
    assert f771.soul_shift == {"floor": 0}
    assert not f770.evolve_any and not f771.evolve_any   # クラシックは単体進化
    raw = dict(proto_card("T770"))
    raw.pop("evolve_from")
    try:
        parse_card(raw, tables)
        raise AssertionError("evolve_from の無い soul_shift が通ってしまった")
    except DefError:
        pass


def test_reduction_is_chosen_base_cost(rules):
    # コスト7 − 進化元コスト5 = 2 を支払う
    e = setup(rules, {"hand": ["T770"], "bz": ["T772"],
                      "mana": ["T001"] * 7}, {})
    top = e.zlist("hand", 0)[0]
    base = e.zlist("bz", 0)[0]
    st, drive = _driver("play:T770", _pick({base}))
    ok = _settle(e, lambda: e.s.cards[top].zone == "bz", drive)
    assert ok and st["played"]
    assert e.s.cards[top].under == [base]
    assert len(_tapped_mana(e)) == 2


def test_choosing_smaller_base_costs_more(rules):
    # 進化元にコスト3を選べば 7−3=4。合計（7−8→床1）でも最大（7−5=2）でもない
    e = setup(rules, {"hand": ["T770"], "bz": ["T772", "T773"],
                      "mana": ["T001"] * 7}, {})
    top = e.zlist("hand", 0)[0]
    small = _by_defn(e, "bz", "T773")[0]
    st, drive = _driver("play:T770", _pick({small}))
    ok = _settle(e, lambda: e.s.cards[top].zone == "bz", drive)
    assert ok and st["played"]
    assert e.s.cards[top].under == [small]
    assert len(_tapped_mana(e)) == 4


def test_floor_one_clamps(rules):
    # コスト7 − 進化元コスト9 は負になるが、floor 1 で 1 を支払う
    e = setup(rules, {"hand": ["T770"], "bz": ["T774"],
                      "mana": ["T001"] * 7}, {})
    top = e.zlist("hand", 0)[0]
    base = e.zlist("bz", 0)[0]
    st, drive = _driver("play:T770", _pick({base}))
    ok = _settle(e, lambda: e.s.cards[top].zone == "bz", drive)
    assert ok and st["played"]
    assert len(_tapped_mana(e)) == 1


def test_floor_zero_free_summon(rules):
    # 無色・コスト5 − 進化元コスト5 = 0。floor 0 なので無支払いで出る
    e = setup(rules, {"hand": ["T775"], "bz": ["T772"],
                      "mana": ["T001"] * 3}, {})
    top = e.zlist("hand", 0)[0]
    base = e.zlist("bz", 0)[0]
    st, drive = _driver("play:T775", _pick({base}))
    ok = _settle(e, lambda: e.s.cards[top].zone == "bz", drive)
    assert ok and st["played"]
    assert e.s.cards[top].under == [base]
    assert _tapped_mana(e) == []


@__import__("pytest").mark.xfail(reason="112.2b（文明数の支払い優先）と第292弾の実効コスト0=支払いなし が競合。docs/vocab-pilot.md 3522 行。どちらの読みを採るか koba の判断待ち", strict=False)
def test_floor_zero_colored_pays_civ_count(rules):
    # 有色（水）・コスト5 − 進化元コスト5 = 0 まで軽減されるが、支払いは
    # 112.2b（コストが文明数を下回れば文明の支払いを優先）で文明数ぶんの1枚になる
    e = setup(rules, {"hand": ["T771"], "bz": ["T772"],
                      "mana": ["T010"] * 3}, {})
    top = e.zlist("hand", 0)[0]
    base = e.zlist("bz", 0)[0]
    st, drive = _driver("play:T771", _pick({base}))
    ok = _settle(e, lambda: e.s.cards[top].zone == "bz", drive)
    assert ok and st["played"]
    assert e.s.cards[top].under == [base]
    assert len(_tapped_mana(e)) == 1


def _main_playable(e, key):
    # 最初の main 決定で key が提示されるか。main は charge の後・attack の前。
    # 提示できる選択肢が無いと main 決定そのものが現れないので、その場合も False。
    seen = {}

    def drive(e, d, keys):
        if d["player"] == 0 and d["kind"] == "main":
            seen["playable"] = key in keys
            return True
        if d["player"] == 1 or (d["player"] == 0 and d["kind"] == "attack"):
            seen["playable"] = False   # main を過ぎた（= main 決定は無かった）
            return True
        return False

    _settle(e, lambda: "playable" in seen, drive, 60)
    return seen["playable"]


def test_not_offered_when_best_base_unpayable(rules):
    # 最良の進化元（コスト5）でも 7−5=2 必要。マナ1では出せない。
    # 旧見積もり（候補合計 7−8→床1）では誤って提示されていた。
    e = setup(rules, {"hand": ["T770"], "bz": ["T772", "T773"],
                      "mana": ["T001"]}, {})
    assert _main_playable(e, "play:T770") is False


def test_offered_when_best_base_payable(rules):
    e = setup(rules, {"hand": ["T770"], "bz": ["T772", "T773"],
                      "mana": ["T001"] * 2}, {})
    assert _main_playable(e, "play:T770") is True
