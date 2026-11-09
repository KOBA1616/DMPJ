"""語彙パイロット第20弾+第21弾（2026-10-31）の検証。

Zラッシュ（キーワード z_rush）は常在型（ユーザーの指摘と公式Q&A 48466で第21弾で作り替え）:
- いずれのプレイヤーのシールドでも、シールドゾーンを離れた際、その時点でバトルゾーンにいる
  Zラッシュ持ち全員のハイパーモードが即座に解放される（誘発ではない）
- シールドが離れた後で出たクリーチャーには適用されない
- 期限は文字通り「次の自分のターンのはじめまで」: 相手のターンに解放されても、
  自分のターンのはじめに戻る
"""
from conftest import setup


def _answer(e, d, plan):
    keys = [o["key"] for o in d["options"]]
    for kind, key in plan:
        if d["kind"] == kind and key in keys:
            e.answer([keys.index(key)])
            return
    if d["kind"] == "yes_no":
        e.answer([keys.index("no")] if "no" in keys else list(range(d["min"])))
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def test_z_rush_window_opens_on_opponents_shield_and_expires_literally(rules):
    # 自分のターンに相手のシールドをブレイクしても窓は開く。そのターンの攻撃で効果が働き、
    # 次の自分のターンのはじめに閉じる
    e = setup(rules, {"bz": ["T060", "T001"]}, {"shield": ["T001", "T001"]})
    beast = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T060")
    assert not e.is_hyper(beast)
    hand_before = len(e.zlist("hand", 0))
    drew = False
    closed = False
    turn0 = None
    for _ in range(80):
        if turn0 is not None and e.s.turn >= turn0 + 2 and e.s.active == 0:
            closed = not e.is_hyper(beast)
            break
        d = e.advance()
        if d is None:
            break
        if e.is_hyper(beast) and turn0 is None:
            turn0 = e.s.turn
        _answer(e, d, [("attack", "attack:T001:player"), ("attack", "attack:T060:player")])
        if len(e.zlist("hand", 0)) > hand_before:
            drew = True
    assert turn0 is not None, "相手のシールドが離れても解放されなかった"
    assert drew, "解放されている間の攻撃で引けなかった"
    assert closed, "次の自分のターンのはじめに戻らなかった"


def test_z_rush_released_on_own_turn_lasts_through_opponents_turn(rules):
    # 自分のターンに相手のシールドをブレイクして解放された場合も、相手ターン中は
    # 解放されたままで、次の自分のターンのはじめに閉じる（公式 QA 48760 の前提）
    e = setup(rules, {"bz": ["T060", "T001"]}, {"shield": ["T001", "T001"]})
    beast = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T060")
    turn0 = None
    opp_samples = []
    closed = False
    for _ in range(160):
        if turn0 is not None:
            if e.s.active == 1 and e.s.turn == turn0 + 1:
                opp_samples.append(e.is_hyper(beast))
            if e.s.turn >= turn0 + 2 and e.s.active == 0:
                closed = not e.is_hyper(beast)
                break
        d = e.advance()
        if d is None:
            break
        if e.is_hyper(beast) and turn0 is None:
            turn0 = e.s.turn
        _answer(e, d, [("attack", "attack:T001:player"), ("attack", "attack:T060:player")])
    assert turn0 is not None, "相手のシールドが離れても解放されなかった"
    assert opp_samples and all(opp_samples), "相手ターン中に解けてしまった"
    assert closed, "次の自分のターンのはじめに戻らなかった"


def test_z_rush_window_closes_at_own_turn_start_when_broken_by_opponent(rules):
    # 相手のターンに自分のシールドがブレイクされても窓は開くが、自分のターンのはじめに閉じる（文字通り）。
    # 相手の2体目の攻撃の判断時点（まだ相手のターン）で開いていることを確認する
    e = setup(rules, {"bz": ["T060"], "shield": ["T001", "T001"]}, {"bz": ["T001", "T001"]})
    beast = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T060")
    opened = False
    for _ in range(40):
        if e.s.active == 0 and e.s.turn > 2:
            break   # 自分のターンが始まった
        if e.s.active == 1 and e.is_hyper(beast):
            opened = True
        d = e.advance()
        if d is None:
            break
        _answer(e, d, [("attack", "attack:T001:player")])
    assert opened, "相手のターンにブレイクされても解放されなかった"
    assert not e.is_hyper(beast), "自分のターンのはじめに戻らなかった"


def test_z_rush_does_not_apply_to_creature_entering_after_shield_left(rules):
    # 公式Q&A 48466: 解放されるのは「シールドが離れた際にバトルゾーンにいる」クリーチャーだけ。
    # 離れた後で出たクリーチャーには適用されない
    e = setup(rules, {"hand": ["T061", "T060"], "shield": ["T001"], "mana": ["T001", "T005", "T005", "T005"]}, {})
    entered_hyper = None
    for _ in range(40):
        tops = [c for c in e.bz_tops(0) if e.s.cards[c].defn == "T060"]
        if tops:
            entered_hyper = e.is_hyper(tops[0])
            break
        d = e.advance()
        if d is None:
            break
        _answer(e, d, [("main", "play:T061"), ("main", "play:T060")])
    assert entered_hyper is False, "シールドが離れた後で出たクリーチャーまで解放されてしまった"
