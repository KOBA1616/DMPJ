"""語彙パイロット第49弾の検証。

mod `no_leave`（「バトルゾーンを離れない」）:
- true: どんな移動でも離れない（破壊・バウンスとも不発）
- {except_destroy: true}: 破壊だけは通し、それ以外の離脱を止める
- {by_opp: true}: 相手の効果による移動だけを止める（by の無い移動は通す）
判定は events の移動適用（置換後の最終移動）で行う。
"""
from conftest import answer, setup


def cast_on(e, spell, player=0):
    """player のメインで spell を唱え、その解決が終わるまで進める。"""
    casted = False
    for _ in range(60):
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d["player"] == player and f"play:{spell}" in keys:
            e.answer([keys.index(f"play:{spell}")])
            casted = True
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if casted and d["kind"] in ("attack", "charge"):
            return
    raise AssertionError("呪文を唱え終わらなかった")


def zone_of(e, defn, owner):
    # 同じ defn のフィラーが山札にもあるため、バトルゾーン/墓地にある個体を優先して探す
    for c in e.s.cards:
        if c.defn == defn and c.controller == owner and c.zone in ("bz", "graveyard"):
            return c.zone
    for c in e.s.cards:
        if c.defn == defn and c.controller == owner:
            return c.zone
    raise AssertionError(defn)


def bz_card(e, defn, owner):
    for bucket in e.s.zones["bz"]:
        for cid in bucket:
            c = e.s.cards[cid]
            if c.defn == defn and c.controller == owner:
                return c
    raise AssertionError(defn)


def test_no_leave_blocks_destroy(rules):
    e = setup(rules, {"hand": ["T056"], "mana": ["T056", "T001", "T001"]},
              {"bz": ["T137"]})
    answer(e, "charge", "pass")   # 先行プレイヤー側のチャージを流す
    cast_on(e, "T056")
    assert zone_of(e, "T137", 1) == "bz"


def test_no_leave_blocks_bounce(rules):
    e = setup(rules, {"hand": ["T140"], "mana": ["T140", "T001", "T001"]},
              {"bz": ["T137"]})
    answer(e, "charge", "pass")
    cast_on(e, "T140")
    assert zone_of(e, "T137", 1) == "bz"


def test_except_destroy_allows_destroy_only(rules):
    e = setup(rules, {"hand": ["T140"], "mana": ["T140", "T001", "T001"]},
              {"bz": ["T138"]})
    answer(e, "charge", "pass")
    cast_on(e, "T140")      # バウンスは止められる
    assert zone_of(e, "T138", 1) == "bz"

    e2 = setup(rules, {"hand": ["T056"], "mana": ["T056", "T001", "T001"]},
               {"bz": ["T138"]})
    answer(e2, "charge", "pass")
    cast_on(e2, "T056")     # 破壊は通る
    assert zone_of(e2, "T138", 1) == "graveyard"


def test_by_opp_granter_protects_others(rules):
    # 守護獣 T139 がいる側のクリーチャーは、相手の破壊呪文では離れない
    e = setup(rules, {"hand": ["T056"], "mana": ["T056", "T001", "T001"]},
              {"bz": ["T139", "T001"]})
    guard = bz_card(e, "T139", 1)
    plain = bz_card(e, "T001", 1)
    answer(e, "charge", "pass")
    cast_on(e, "T056")
    assert guard.zone == "bz"
    assert plain.zone == "bz"

    # 守護獣がいなければ通常どおり破壊される（対照）
    e2 = setup(rules, {"hand": ["T056"], "mana": ["T056", "T001", "T001"]},
               {"bz": ["T001"]})
    plain2 = bz_card(e2, "T001", 1)
    answer(e2, "charge", "pass")
    cast_on(e2, "T056")
    assert plain2.zone == "graveyard"


def test_except_battle_granter(rules):
    # 破壊呪文は止められる（バトル敗北ではないため）
    e = setup(rules, {"hand": ["T056"], "mana": ["T056", "T001", "T001"]},
              {"bz": ["T141", "T142"]})
    big = bz_card(e, "T142", 1)
    answer(e, "charge", "pass")
    cast_on(e, "T056")
    assert big.zone == "bz"

    # バトルに負けたら離れる: 巨獣がプレイヤーを攻撃してタップ → 超巨獣が攻撃して勝つ
    e2 = setup(rules, {"hand": ["T143"], "mana": ["T143", "T001", "T001", "T001", "T001"]},
               {"bz": ["T141", "T142"]})
    big2 = bz_card(e2, "T142", 1)
    # 先行は P1: 巨獣でプレイヤーを攻撃させる
    for _ in range(30):
        d = e2.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and d["player"] == 1 and any(k.startswith("attack:T142") for k in keys):
            e2.answer([next(i for i, k in enumerate(keys) if k.startswith("attack:T142"))])
            break
        if "pass" in keys:
            e2.answer([keys.index("pass")])
        else:
            e2.answer(list(range(d["min"])))
    # 攻撃の解決（シールドブレイク等）が終わり、P0 のターンに入るまで進める
    for _ in range(30):
        if big2.tapped:
            break
        d = e2.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        e2.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert big2.tapped
    # P0: 超巨獣を召喚してタップしている巨獣を攻撃
    for _ in range(60):
        d = e2.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d["player"] == 0 and "play:T143" in keys:
            e2.answer([keys.index("play:T143")])
        elif d["kind"] == "pay_mana":
            e2.answer(list(range(d["min"])))
        elif d["kind"] == "attack" and d["player"] == 0 and any(k.startswith("attack:T143:") for k in keys):
            tgt = next((k for k in keys if k == "attack:T143:T142"), None)
            if tgt is None:
                e2.answer([keys.index("pass")])
                continue
            e2.answer([keys.index(tgt)])
            break
        elif "pass" in keys:
            e2.answer([keys.index("pass")])
        else:
            e2.answer(list(range(d["min"])))
    for _ in range(10):
        if big2.zone == "graveyard":
            break
        d = e2.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        e2.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert big2.zone == "graveyard"
