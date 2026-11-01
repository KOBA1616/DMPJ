"""語彙パイロット第29弾（フェーズ7）: 進化V（フィルタごとの進化元）/ 代替コスト（別額・行動形式）。"""
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


def test_evolution_v(rules):
    """進化V: 光のクリーチャーと自然のクリーチャーを1体ずつ重ねて進化する。"""
    e = setup(rules, {"bz": ["T004", "T001"], "hand": ["T089"], "mana": ["T004"] * 5 + ["T001"]}, {})

    def drive(e, d, keys):
        if d["kind"] == "choose_evo_source":
            e.answer([0])
            return True
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if k == "play:T089"]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T089" for c in e.zlist("bz", 0)), drive, 200)
    cid = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T089")
    assert len(e.s.cards[cid].under) == 2   # 進化元は2体とも下にいる


def test_evolution_v_needs_both_civs(rules):
    """進化V: 片方の文明の進化元しかいなければ選択肢に出ない。"""
    e = setup(rules, {"bz": ["T004"], "hand": ["T089"], "mana": ["T004"] * 5 + ["T001"]}, {})
    found = {}

    def drive(e, d, keys):
        if any(k == "play:T089" for k in keys):
            found["opt"] = True
        return False

    _settle(e, lambda: False, drive, 40)
    assert not found.get("opt")


def test_alt_cost_spell(rules):
    """代替コスト（別額）: [光光4] で唱えると追加の1ドローが付く（合計3ドロー）。"""
    e = setup(rules, {"hand": ["T090"], "mana": ["T004", "T004", "T004", "T004"]}, {})
    h0 = len(e.zlist("hand", 0))

    def drive(e, d, keys):
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if k == "play:T090:alt"]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: len(e.zlist("hand", 0)) == h0 + 2, drive, 200)   # -1（唱えた）+3ドロー


def test_alt_cost_do_form(rules):
    """代替コスト（行動形式）: 闇のカード2枚を捨て、自分の闇クリーチャー1体を破壊して唱える。"""
    e = setup(rules, {"hand": ["T091", "T008", "T008"], "bz": ["T008"]}, {})
    g0 = len(e.zlist("graveyard", 0))

    def drive(e, d, keys):
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if k == "play:T091:alt"]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    ok = _settle(e, lambda: len(e.zlist("graveyard", 0)) >= g0 + 4, drive, 250)   # 捨て2+破壊1+呪文自身1
    assert ok
    assert any(e.s.cards[c].defn == "T091" for c in e.zlist("graveyard", 0))
