"""語彙パイロット第30弾（フェーズ8）: ビビッドロー（引いたターンの表向き+代替コスト）/
強制攻撃（キーワード must_attack = require）/ 究極進化（evolve_from の types フィルタ・既存）。"""
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


def test_vividraw(rules):
    """ビビッドロー: ドローステップで引いたカードを表向きにし、[水火2] で召喚できる。"""
    e = setup(rules, {"hand": ["T092"], "mana": ["T003", "T005"]}, {})
    t092 = next(c for c in e.zlist("hand", 0) if e.s.cards[c].defn == "T092")
    e._raw_move(t092, "deck", "top")   # 山札の一番上に置き、最初のドローで引かせる
    state = {}

    def drive(e, d, keys):
        if d["kind"] == "main":
            if "reveal:T092" in keys:
                state["revealed"] = True
                e.answer([keys.index("reveal:T092")])
                return True
            hit = [i for i, k in enumerate(keys) if k == "play:T092:vivid"]
            if hit:
                state["vivid_opt"] = True
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T092" for c in e.zlist("bz", 0)), drive, 300)
    assert state.get("revealed") and state.get("vivid_opt")


def test_must_attack_forces_attack_step(rules):
    """強制攻撃: require[attack] により、自分のターンに自動的に攻撃する（タップする）。"""
    e = setup(rules, {"bz": ["T093"]}, {"bz": ["T001"]})
    cid = next(iter(e.bz_tops(0)))
    e.s.cards[cid].entered_turn = -1
    assert not e.s.cards[cid].tapped
    assert _settle(e, lambda: e.s.cards[cid].tapped, None, 120)


def test_ultimate_evolution(rules):
    """究極進化: 進化クリーチャーの上にだけ重ねられる。"""
    e = setup(rules, {"bz": ["T087"], "hand": ["T094"], "mana": ["T008"] * 7}, {})
    # T087 は進化クリーチャー（このシナリオでは素のクリーチャーとして場に出ている扱い）
    def drive(e, d, keys):
        if d["kind"] == "choose_evo_source":
            e.answer([0])
            return True
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if k == "play:T094"]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T094" for c in e.zlist("bz", 0)), drive, 200)
