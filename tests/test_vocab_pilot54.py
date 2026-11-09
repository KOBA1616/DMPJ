"""語彙パイロット第54弾: ビビッドロー使用の可視化。

ビビッドローで実行したことを (1) 移動/詠唱イベントの vivid 印（他カードの誘発の
when: {vivid: true} 照合）、(2) 解決 env の vivid_paid（呪文自身の分岐条件）、
(3) filter の vividraw 所持判定、の3経路で参照できるようにした。代替コストの
alt / alt_paid（selectors）と同じ型。
"""
from conftest import setup


def _settle(e, done, drive=None, max_steps=300):
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


def _vivid_drive(target_defn, state):
    def drive(e, d, keys):
        if d["kind"] == "main":
            rk = f"reveal:{target_defn}"
            if rk in keys:
                state["revealed"] = True
                e.answer([keys.index(rk)])
                return True
            hit = [i for i, k in enumerate(keys) if k == f"play:{target_defn}:vivid"]
            if hit:
                state["vivid_opt"] = True
                e.answer([hit[0]])
                return True
        return False
    return drive


def test_trigger_fires_on_vivid_summon(rules):
    """T149: 自分のクリーチャーがビビッドローで召喚された時、1ドロー。

    判別形（第149弾で補強）: 手札の枚数は「入場直後の Decision 提示時点」で見る。
    以前の形（入場後に手札が1枚になるまで進める）は、次の自分のターンのドローでも
    満たされてしまい、誘発が発火しなくても通る非判別なものだった。実際、誘発収集
    レコードに vivid の印が写らない潜在バグでこの誘発は発火していなかった。"""
    e = setup(rules, {"bz": ["T149"], "hand": ["T092"], "mana": ["T003", "T005"]}, {})
    t092 = next(c for c in e.zlist("hand", 0) if e.s.cards[c].defn == "T092")
    e._raw_move(t092, "deck", "top")   # 最初のドローで引かせる
    state = {}
    hand_at_entry = None
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        if any(e.s.cards[c].defn == "T092" for c in e.zlist("bz", 0)):
            hand_at_entry = len(e.zlist("hand", 0))   # 誘発は Decision 提示前に解決済み
            break
        keys = [o["key"] for o in d["options"]]
        if _vivid_drive("T092", state)(e, d, keys):
            continue
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert state.get("revealed") and state.get("vivid_opt")
    assert hand_at_entry == 1   # 入場直後に誘発で1枚引いた（手札0→1）


def test_trigger_silent_on_normal_summon(rules):
    """通常コストで召喚した場合は誘発しない。"""
    e = setup(rules, {"bz": ["T149"], "hand": ["T092"], "mana": ["T003", "T005", "T001", "T001"]}, {})

    def drive(e, d, keys):
        if d["kind"] == "main" and "play:T092" in keys:
            e.answer([keys.index("play:T092")])
            return True
        return False

    ok = _settle(e, lambda: any(e.s.cards[c].defn == "T092" for c in e.zlist("bz", 0)), drive)
    assert ok
    assert len(e.zlist("hand", 0)) == 0   # ドロー誘発なし


def test_vivid_paid_branch_on_spell(rules):
    """T150: ビビッドローで唱えた時だけ追加ドロー（vivid_paid 条件）。"""
    e = setup(rules, {"hand": ["T150"], "mana": ["T003"]}, {})
    t150 = next(c for c in e.zlist("hand", 0) if e.s.cards[c].defn == "T150")
    e._raw_move(t150, "deck", "top")
    state = {}
    ok = _settle(e, lambda: any(e.s.cards[c].defn == "T150" for c in e.zlist("graveyard", 0)),
                 _vivid_drive("T150", state))
    assert state.get("vivid_opt") and ok
    assert len(e.zlist("hand", 0)) == 2   # 1 + vivid_paid の追加1


def test_vivid_paid_branch_off_when_normal_cast(rules):
    e = setup(rules, {"hand": ["T150"], "mana": ["T003", "T001", "T001"]}, {})

    def drive(e, d, keys):
        if d["kind"] == "main" and "play:T150" in keys:
            e.answer([keys.index("play:T150")])
            return True
        return False

    ok = _settle(e, lambda: any(e.s.cards[c].defn == "T150" for c in e.zlist("graveyard", 0)), drive)
    assert ok
    assert len(e.zlist("hand", 0)) == 1   # 通常分岐のみ


def test_vividraw_filter(rules):
    """T151: filter {vividraw: true} はビビッドロー所持者だけを選ぶ。"""
    e = setup(rules, {"bz": ["T092", "T001"], "hand": ["T151"], "mana": ["T001", "T001"]}, {})
    state = {}

    def drive(e, d, keys):
        if d["kind"] == "charge" and not state.get("tapped"):
            for c in e.zlist("bz", 0):
                e.s.cards[c].tapped = True
            state["tapped"] = True
            e.answer([keys.index("pass")])
            return True
        if d["kind"] == "main" and "play:T151" in keys:
            e.answer([keys.index("play:T151")])
            return True
        return False

    def done():
        t092 = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T092")
        t001 = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T001")
        return not e.s.cards[t092].tapped and e.s.cards[t001].tapped

    assert _settle(e, done, drive)
