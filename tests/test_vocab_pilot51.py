"""語彙パイロット第51弾（フェーズ17）: must_be_attacked（攻撃先の強制）。

「相手のクリーチャーが攻撃する時、可能ならこのクリーチャーを攻撃する」を
mod の must_be_attacked: true で表す。攻撃側の合法な攻撃先に誘引持ちが含まれれば、
攻撃先は誘引持ちだけに限られる（プレイヤーも他のクリーチャーも選べない）。
誘引持ちが合法な攻撃先でない時（アンタップしていて攻撃できない等）は制限しない。
"""
from conftest import setup, answer


def _attack_keys(e, player):
    """指定プレイヤーの攻撃ステップの決定まで進め、攻撃キーの一覧を返す。"""
    for _ in range(60):
        d = e.advance()
        assert d is not None
        if d["kind"] == "attack" and d["player"] == player:
            return [o["key"] for o in d["options"]], d
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("attack step not reached")


def _tap(e, player, defn):
    for c in e.zlist("bz", player):
        if e.s.cards[c].defn == defn:
            e.s.cards[c].tapped = True
            return
    raise AssertionError(defn)


def test_taunt_restricts_targets(rules):
    """タップしている誘引獣（T146）がいれば、攻撃先はそちらだけになる。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T146", "T001"]})
    _tap(e, 1, "T146")
    _tap(e, 1, "T001")
    keys, _ = _attack_keys(e, 0)
    attacks = [k for k in keys if k.startswith("attack:")]
    assert attacks == ["attack:T005:T146"]


def test_untapped_taunt_does_not_restrict(rules):
    """誘引獣がアンタップしていて攻撃できない時は、制限は働かない（可能なら、の範囲）。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T146", "T001"]})
    _tap(e, 1, "T001")
    keys, _ = _attack_keys(e, 0)
    attacks = sorted(k for k in keys if k.startswith("attack:"))
    assert attacks == ["attack:T005:T001", "attack:T005:player"]


def test_granted_taunt_until_next_turn(rules):
    """呪文（T147）で付与した誘引も、次の自分のターンのはじめまで相手の攻撃先を制限する。"""
    e = setup(rules, {"bz": ["T004"], "hand": ["T147"], "mana": ["T001", "T005"]},
              {"bz": ["T005"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T147")
    # マナ支払い（2枚しかない）と対象（自分のクリーチャー1体だけ）は自動で決まる。
    # タップして合法な攻撃先にしておく
    _tap(e, 0, "T004")
    keys, _ = _attack_keys(e, 1)
    attacks = [k for k in keys if k.startswith("attack:")]
    assert attacks == ["attack:T005:T004"]
