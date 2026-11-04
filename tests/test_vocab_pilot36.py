"""語彙パイロット第36弾（フェーズ14）:
- 素の墓地召喚 summon_from_graveyard（単独17件）: キーワードで許可だけ与え、アビスラッシュの付随処理（召喚酔いでもプレイヤー攻撃可・ターン終わりに山札の下）は付けない。
- 墓地進化 graveyard_evolution（単独17件）: 進化クリーチャー型は evolve_zone: graveyard で既存可。通常クリーチャー型は面の grave_evo: true で「:gevo」選択肢（通常召喚も可能）。
"""
from conftest import setup


def _settle(e, done, drive=None, max_steps=150):
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


def test_plain_graveyard_summon_no_rush_extras(rules):
    """墓地から通常コストで召喚でき、ターン終わりに山札の下へは行かない。"""
    e = setup(rules, {"graveyard": ["T111"], "mana": ["T008"] * 4}, {"hand": []})
    cid = e.zlist("graveyard", 0)[0]
    st = {}

    def drive(e, d, keys):
        if d["kind"] == "main" and d["player"] == 0 and not st.get("played"):
            hit = [i for i, k in enumerate(keys) if k == "play:T111:rush"]
            if hit:
                st["played"] = True
                e.answer([hit[0]])
                return True
        if d["kind"] == "pay_mana" and d["player"] == 0:
            e.answer([0])
            return True
        return False

    ok = _settle(e, lambda: bool(st.get("played")) and e.s.cards[cid].zone == "bz"
                 and e.s.turn >= 2, drive, 300)
    assert ok
    assert e.s.cards[cid].zone == "bz"          # アビスラッシュと違い、山札の下へは行かない


def test_graveyard_evolution(rules):
    """墓地進化: 手札から、自分の墓地の闇クリーチャーの上に重ねて出す。通常召喚の選択肢も出る。"""
    e = setup(rules, {"hand": ["T112"], "graveyard": ["T008"], "mana": ["T008"] * 6}, {})
    top = e.zlist("hand", 0)[0]
    base = e.zlist("graveyard", 0)[0]
    st = {}

    def drive(e, d, keys):
        if d["kind"] == "main" and d["player"] == 0 and not st.get("played"):
            st["saw_plain"] = "play:T112" in keys
            hit = [i for i, k in enumerate(keys) if k == "play:T112:gevo"]
            if hit:
                st["played"] = True
                e.answer([hit[0]])
                return True
        if d["kind"] == "choose_evo_source" and d["player"] == 0:
            e.answer([0])
            return True
        if d["kind"] == "pay_mana" and d["player"] == 0:
            e.answer([0])
            return True
        return False

    assert _settle(e, lambda: e.s.cards[top].zone == "bz" and e.s.cards[top].under == [base], drive, 200)
    assert st["saw_plain"] is True                       # 通常召喚も選べる
    assert e.s.cards[base].zone == "bz"                  # 進化元は墓地からバトルゾーンへ（下のカードとして）
    assert "evolution" in e.chars(top)["types"]          # 重なっている間は進化クリーチャーとして扱う
