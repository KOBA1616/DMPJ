"""語彙パイロット第5弾（2026-10-30）の検証。

式 `entered: {owner, other?}`: このターン、そのプレイヤーがバトルゾーンに出したクリーチャーの数。
バトルゾーンへの move を適用するたびに turn_counters へ記録し、ターン開始でリセットされる
（rejects: entered_this_turn_condition）。
「２体目」は cmp の >= と < の組み合わせで書く（cmp に = は無い）。
"""
from conftest import answer, setup


def _answer_default(e, d, prefer=None):
    keys = [o["key"] for o in d["options"]]
    if prefer and prefer in keys:
        e.answer([keys.index(prefer)])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def play(e, defn, pay_key=None):
    """メインで1体出し、支払いまで済ませて次のメイン/攻撃の判断で止める。
    出せるものが他に無く攻撃もできないと判断が出ずにターンが進むので、ターン変化でも止める。"""
    played = False
    turn = e.s.turn
    for _ in range(40):
        d = e.advance()
        assert d is not None
        if played and e.s.turn != turn:
            return
        if d["kind"] == "main" and not played:
            _answer_default(e, d, prefer=f"play:{defn}")
            played = True
        elif d["kind"] == "pay_mana":
            _answer_default(e, d, prefer=pay_key)
        elif played and d["kind"] in ("main", "attack"):
            return
        else:
            _answer_default(e, d)
    raise AssertionError("play did not finish")


def attack_options(e):
    """このターンの攻撃判断の選択肢。攻撃できるクリーチャーがいなければ判断自体が出ないので、
    ターンが変わったら空（攻撃不可）として返す。"""
    turn = e.s.turn
    for _ in range(40):
        d = e.advance()
        assert d is not None
        if e.s.turn != turn:
            return []
        if d["kind"] == "attack":
            return [o["key"] for o in d["options"]]
        _answer_default(e, d)
    raise AssertionError("attack phase not reached")


def test_entered_other_grants_speed_attacker(rules):
    """先に別のクリーチャーを出していれば、追随兵はスピードアタッカーを得て攻撃できる。"""
    e = setup(rules, {"hand": ["T001", "T036"], "mana": ["T008", "T001", "T001", "T001"]}, {})
    answer(e, "charge", "pass")
    play(e, "T001", pay_key="mana:T001,T001")   # 闇マナ T008 は T036 のために残す
    play(e, "T036")
    opts = attack_options(e)
    assert any(o.startswith("attack:T036:") for o in opts), opts


def test_entered_other_not_granted_when_first(rules):
    """そのターン最初のクリーチャーなら付与されず、召喚酔いで攻撃できない。"""
    e = setup(rules, {"hand": ["T036"], "mana": ["T008", "T001"]}, {})
    answer(e, "charge", "pass")
    play(e, "T036")
    opts = attack_options(e)
    assert not any(o.startswith("attack:T036:") for o in opts), opts


def test_entered_count_lifts_attack_deny(rules):
    """慎重兵は、そのターン自分のクリーチャーが2体以上出るまでは攻撃できない。"""
    e = setup(rules, {"bz": ["T037"], "hand": ["T001"], "mana": ["T001", "T001"]}, {})
    answer(e, "charge", "pass")
    play(e, "T001")          # このターン1体目: まだ攻撃できない
    opts = attack_options(e)
    assert not any(o.startswith("attack:T037:") for o in opts), opts
    # 2体出せば攻撃できる
    e2 = setup(rules, {"bz": ["T037"], "hand": ["T001", "T002"], "mana": ["T001", "T001", "T001", "T001"]}, {})
    answer(e2, "charge", "pass")
    play(e2, "T001")
    play(e2, "T002")
    opts = attack_options(e2)
    assert any(o.startswith("attack:T037:") for o in opts), opts
