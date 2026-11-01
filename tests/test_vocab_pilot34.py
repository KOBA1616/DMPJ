"""語彙パイロット第34弾（フェーズ12）:
- 離脱置換（leave_replacement）は既存の replace で表せることの確認
  （とどまる型＝ instead: []、行き先変更型＝ instead で {ref: subject} を別ゾーンへ、身代わり型＝ optional ＋ instead で破壊）
- 出現置換（entry_replacement）も既存の replace で表せることの確認（相手の登場を墓地送りに置換）
- filter に neo を追加（NEOクリーチャーを指す。G-NEO も neo: true を持つ）
"""
from conftest import setup


def _settle(e, done, drive=None, max_steps=120):
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


def _opp_destroy(e, target_defn):
    """相手（P1）が T006（パワー4000以下を破壊）で target_defn を狙う drive。"""
    def drive(e, d, keys):
        if d["kind"] == "choose_cards":
            hit = [i for i, k in enumerate(keys) if target_defn in k]
            if hit:
                e.answer([hit[0]])
                return True
        if d["kind"] == "main" and d["player"] == 1:
            hit = [i for i, k in enumerate(keys) if k == "play:T006"]
            if hit:
                e.answer([hit[0]])
                return True
        return False
    return drive


def test_stay_replacement(rules):
    """とどまる型: 破壊されても、パワーが正ならバトルゾーンに留まる。"""
    e = setup(rules, {"bz": ["T105"]}, {"hand": ["T006"], "mana": ["T005"] * 3})
    drive = _opp_destroy(e, "T105")
    assert _settle(e, lambda: e.s.turn > 2, drive, 400)
    assert any(e.s.cards[c].defn == "T105" for c in e.zlist("bz", 0))
    assert not any(e.s.cards[c].defn == "T105" for c in e.zlist("graveyard", 0))


def test_destination_change_replacement(rules):
    """行き先変更型: 自分のクリーチャーが離れる時、かわりに山札の下に置く。"""
    e = setup(rules, {"bz": ["T108", "T001"]}, {"hand": ["T006"], "mana": ["T005"] * 3})
    drive = _opp_destroy(e, "T001")
    target = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T001")
    assert _settle(e, lambda: e.s.cards[target].zone == "deck", drive, 400)
    assert e.zlist("deck", 0)[-1] == target   # 山札の一番下に置かれた
    assert not any(e.s.cards[c].defn == "T001" for c in e.zlist("graveyard", 0))


def test_substitute_replacement(rules):
    """身代わり型: 他のクリーチャーが離れる時、かわりに自分のクリーチャーを1体破壊してもよい。"""
    e = setup(rules, {"bz": ["T107", "T001"]}, {"hand": ["T006"], "mana": ["T005"] * 3})

    def drive(e, d, keys):
        if d["kind"] == "choose_replacement":
            hit = [i for i, k in enumerate(keys) if "T107" in k]
            if hit:
                e.answer([hit[0]])
                return True
        if d["kind"] == "choose_cards" and d["player"] == 0:
            hit = [i for i, k in enumerate(keys) if "T107" in k]
            if hit:
                e.answer([hit[0]])
                return True
        if d["kind"] == "choose_cards":
            hit = [i for i, k in enumerate(keys) if "T001" in k]
            if hit:
                e.answer([hit[0]])
                return True
        if d["kind"] == "main" and d["player"] == 1:
            hit = [i for i, k in enumerate(keys) if k == "play:T006"]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T107" for c in e.zlist("graveyard", 0)), drive, 400)
    assert any(e.s.cards[c].defn == "T001" for c in e.zlist("bz", 0))   # 本来の対象は残った


def test_entry_replacement(rules):
    """出現置換: 相手のクリーチャーが出る時、かわりに墓地に置く。"""
    e = setup(rules, {"hand": ["T001"], "mana": ["T001", "T001"]}, {"bz": ["T106"]})

    def drive(e, d, keys):
        if d["kind"] == "main" and d["player"] == 0:
            hit = [i for i, k in enumerate(keys) if k == "play:T001"]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T001" for c in e.zlist("graveyard", 0)), drive, 300)
    assert not any(e.s.cards[c].defn == "T001" for c in e.zlist("bz", 0))


def test_neo_filter(rules):
    """filter の neo: NEO進化を持つカードだけにマッチする（G-NEO も neo: true を持つ）。"""
    e = setup(rules, {"bz": ["T101", "T001"]}, {})
    by_defn = {e.s.cards[c].defn: c for c in e.zlist("bz", 0)}
    assert e.filter_match(by_defn["T101"], {"neo": True})
    assert not e.filter_match(by_defn["T001"], {"neo": True})
    assert e.filter_match(by_defn["T001"], {"neo": False})
