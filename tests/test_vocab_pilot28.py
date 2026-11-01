"""語彙パイロット第28弾（フェーズ6）: アバレチェーン（may の else）/ ヨビニオン（キーワード+op）/
マナゾーンからの召喚（許可）/ シンカパワー（stacked 照合）/ 進化でないフィルタ（not_types・既存）/
オシオキムーン（既存の when で表現可）。"""
from conftest import setup


def _settle(e, done, drive=None, max_steps=90):
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


def test_abare_chain_else(rules):
    """アバレチェーン: そのターン最初の攻撃で may を断ると else（1ドロー）が実行される。"""
    e = setup(rules, {"bz": ["T083", "T005"]}, {})
    atk = next(iter(e.bz_tops(0)))
    e.s.cards[atk].entered_turn = -1
    h0 = len(e.zlist("hand", 0))

    def drive(e, d, keys):
        if d["kind"] == "declare_attack" and d["player"] == 0:
            e.answer([0])
            return True
        if d["kind"] == "yes_no":
            e.answer([keys.index("no")])
            return True
        return False

    assert _settle(e, lambda: len(e.zlist("hand", 0)) == h0 + 1, drive, 150)


def test_yobinion(rules):
    """ヨビニオン: 召喚で出た時、山札の上からコストの小さいクリーチャー（T001・2）が場に出る。"""
    e = setup(rules, {"hand": ["T084"], "mana": ["T001", "T001", "T001", "T001"]}, {})
    deck = e.s.zones["deck"][0]
    t005s = [c for c in deck if e.s.cards[c].defn == "T002"]
    small = [c for c in deck if e.s.cards[c].defn == "T001"][:2]
    rest = [c for c in deck if c not in small]
    e.s.zones["deck"][0] = small + rest   # 上から T001, T001, ... 最初の小さいクリーチャーは先頭の T001

    def drive(e, d, keys):
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if "T084" in k and not k.startswith("charge:")]
            if hit:
                e.answer([hit[0]])
                return True
            if d["kind"] == "yes_no":
                e.answer([keys.index("yes")])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T084" for c in e.zlist("bz", 0)), drive, 200)
    assert _settle(e, lambda: sum(1 for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T001") >= 1, None, 200)


def test_summon_from_mana(rules):
    """マナゾーンから召喚: 「:msum」選択肢が出て、通常コストで召喚できる。"""
    e = setup(rules, {"mana": ["T086", "T001", "T001"]}, {})
    seen = {}

    def drive(e, d, keys):
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if "T086" in k and "msum" in k]
            if hit:
                seen["opt"] = True
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T086" for c in e.zlist("bz", 0)), drive, 200)
    assert seen.get("opt")


def test_shinka_power(rules):
    """シンカパワー: 進化として重ねて出た時に誘発してドローする。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T087"], "mana": ["T003", "T003", "T003", "T003", "T003"]}, {})
    h_after_play = {}

    def drive(e, d, keys):
        if d["kind"] == "choose_evo_source":
            e.answer([0])
            return True
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if k == "play:T087"]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T087" for c in e.zlist("bz", 0)), drive, 200)
    h_after_play["n"] = len(e.zlist("hand", 0))
    assert _settle(e, lambda: len(e.zlist("hand", 0)) == h_after_play["n"] + 1, None, 200)


def test_not_evolution_filter(rules):
    """「進化ではないクリーチャーを手札から出す」は not_types で表せる（対象なしでも壊れない）。"""
    e = setup(rules, {"hand": ["T088"], "mana": ["T004"] * 6}, {})

    def drive(e, d, keys):
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if "T088" in k and not k.startswith("charge:")]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T088" for c in e.zlist("bz", 0)), drive, 200)
    assert _settle(e, lambda: len(e.zlist("bz", 0)) == 1, None, 80)
