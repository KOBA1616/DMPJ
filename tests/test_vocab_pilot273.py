"""第273弾: evolution_base_any — evolve_base_any 許可の種族肩代わりを race_has 形と
any_of の枝まで広げる（第232弾の _evo_match 拡張）。

対象ギャップ evolution_base_any の4枚（dmex08-137 / dmex16-014 / dmx21-062 /
dmx22a-041）は「どの種族の進化クリーチャーを置いてもよい」を持つ。進化側の要求は
{races} 形だけでなく {civs, race_has} 形や any_of の枝にも現れるため、許可の
肩代わりは「種族指定を取り除いた残りの照合」として一般化した。
"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _drive_to_main(e, want_key, max_steps=60):
    """want_key で始まるキーが main 選択肢に出るまで進める。出なければ None。"""
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


def _play_evolution(e, evo, base):
    d, keys = _drive_to_main(e, f"play:{evo}")
    assert d is not None, f"{evo} のプレイ選択肢が出ない"
    e.answer([next(i for i, k in enumerate(keys) if k.startswith(f"play:{evo}"))])
    _finish_play(e)
    assert evo in _defns(e, "bz", 0)
    top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == evo)
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == [base]


def test_pilot273_protos_parse():
    rules = _rules()
    for pid in ("T764", "T765", "T766", "T767", "T768", "T769"):
        assert pid in rules.cards, pid


def test_race_has_civ_evolution_on_matching_civ_permission_base():
    """{civs: fire, race_has: ドラゴン}: 火の許可持ち（種族はドラゴンでない）に置ける。"""
    e = setup(_rules(), {"bz": ["T764"], "hand": ["T767"],
                         "mana": ["T551"] * 5}, {})
    _play_evolution(e, "T767", "T764")


def test_race_has_civ_requirement_not_waived():
    """文明指定は許可で肩代わりしない: 自然の許可持ちには火ドラゴン進化は置けない。"""
    e = setup(_rules(), {"bz": ["T766"], "hand": ["T767"],
                         "mana": ["T551"] * 5}, {})
    d, _ = _drive_to_main(e, "play:T767", max_steps=10)
    assert d is None


def test_race_has_no_permission_no_waiver():
    """許可のない火クリーチャー（種族はドラゴンでない）には置けない。"""
    e = setup(_rules(), {"bz": ["T034"], "hand": ["T767"],
                         "mana": ["T551"] * 5}, {})
    d, _ = _drive_to_main(e, "play:T767", max_steps=10)
    assert d is None


def test_any_of_race_branch_waived():
    """any_of の種族枝も肩代わりする: 自然の許可持ちにドラゴン/水進化を置ける。"""
    e = setup(_rules(), {"bz": ["T766"], "hand": ["T768"],
                         "mana": ["T002"] * 4}, {})
    _play_evolution(e, "T768", "T766")


def test_any_of_no_permission_no_waiver():
    """許可のない闇クリーチャーには any_of（ドラゴン/水）進化は置けない。"""
    e = setup(_rules(), {"bz": ["T619"], "hand": ["T768"],
                         "mana": ["T002"] * 4}, {})
    d, _ = _drive_to_main(e, "play:T768", max_steps=10)
    assert d is None


def test_evo_reduce_on_permission_base():
    """dmex16-014 形: 許可＋evo_reduce の進化元からはコスト4進化を3マナで置ける。"""
    e = setup(_rules(), {"bz": ["T765"], "hand": ["T627"],
                         "mana": ["T551"] * 3}, {})
    d, keys = _drive_to_main(e, "play:T627")
    assert d is not None
    e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T627"))])
    for _ in range(40):   # T627 が場に出た瞬間に止める（ターンを跨ぐとマナが起きる）
        if "T627" in _defns(e, "bz", 0):
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] in ("pay_mana", "choose_evo_source"):
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T627")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T765"]
    mana = e.zlist("mana", 0)
    assert sum(1 for c in mana if e.s.cards[c].tapped) == 3   # 軽減後の3を全て支払った


def test_no_reduce_on_plain_permission_base():
    """軽減のない許可持ち（T764）ではコスト4進化は3マナで置けない。"""
    e = setup(_rules(), {"bz": ["T764"], "hand": ["T627"],
                         "mana": ["T551"] * 3}, {})
    d, _ = _drive_to_main(e, "play:T627", max_steps=10)
    assert d is None


def test_destroy_trigger_puts_dragon_from_hand():
    """dmex08-137 形: 破壊された時、手札からドラゴンを出してもよい。"""
    e = setup(_rules(), {"bz": ["T764"], "hand": ["T620", "T769"],
                         "mana": ["T551"] * 3}, {})
    for _ in range(120):
        if "T769" in _defns(e, "bz", 0):
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main":
            hit = [i for i, k in enumerate(keys) if k.startswith("play:T620")]
            e.answer([hit[0]] if hit else [keys.index("pass")])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif d["kind"] in ("choose_cards", "choose_card"):
            pref = [i for i, k in enumerate(keys) if "T764" in k or "T769" in k]
            e.answer([pref[0]] if pref else list(range(d["min"])))
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "T764" in _defns(e, "graveyard", 0)
    assert "T769" in _defns(e, "bz", 0)
