"""語彙パイロット（2026-10-30）の検証: 小さい語彙の動作。

- move の tapped: 「タップしてマナゾーンに置く」（rejects: tapped_mana_placement。main に既存だったので動作確認のみ）
- tap の no_untap_next: 「次の相手のターンのはじめにアンタップしない」（freeze 系／does_not_untap_next_turn）
- キーワード enters_tapped: 「タップしてバトルゾーンに出る」（enters_tapped）
- op force_battle: 「選んだクリーチャーとこのクリーチャーをバトルさせる」（force_battle）

支払いの組み合わせが1通りだけの時は pay_mana の決定は出ない（ask の一意自動決定）。
マナに使うカードは文明が合うものを使う（T001=自然, T003=水, T005=火）。
"""
from conftest import answer, setup


def names(e, z, p):
    return sorted(e.s.cards[c].defn for c in e.zlist(z, p))


def bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def advance_until(e, pred, limit=120):
    """pass できる決定は pass し、それ以外は最小数を選んで、pred が真になるまで進める。"""
    for _ in range(limit):
        if pred():
            return
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert pred()


def test_move_tapped_puts_mana_tapped(rules):
    """山札の上から2枚がタップ状態でマナゾーンに置かれる（単色なので通常の配置ではアンタップのはず）。"""
    e = setup(rules, {"hand": ["T023"], "mana": ["T001"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T023")
    e.advance()
    mana = e.zlist("mana", 0)
    assert len(mana) == 3                                   # 支払った1枚 + 新しく置いた2枚
    assert all(e.s.cards[c].tapped for c in mana)           # 支払いで1枚、新規2枚も tapped 指定で全てタップ


def test_tap_no_untap_next_skips_one_untap(rules):
    """凍結した相手クリーチャーは、次の相手ターン開始時にアンタップせず、その次のターン開始時にはアンタップする。"""
    e = setup(rules, {"hand": ["T024"], "mana": ["T003"]}, {"bz": ["T004"]})
    tgt = bz(e, 1, "T004")
    answer(e, "charge", "pass")
    answer(e, "main", "play:T024")
    d = e.advance()                                         # 対象は1体だけなので選択は自動。
    # advance は次の決定（相手ターンの charge）まで進むので、この時点で相手ターン開始時の
    # アンタップ判定は終わっている: タップされたままで、印は消費されているはず
    assert e.s.active == 1 and d["kind"] == "charge"
    assert e.s.cards[tgt].tapped and not e.s.cards[tgt].no_untap_next   # アンタップされず、印は消費された
    turn1 = e.s.turn
    advance_until(e, lambda: e.s.active == 1 and e.s.turn > turn1 and e.s.step == "charge")
    assert not e.s.cards[tgt].tapped                        # 今度は通常どおりアンタップする


def test_tap_no_untap_next_sets_flag_until_consumed(rules):
    """印そのものの確認: tap の解決直後（ターンが変わる前）は no_untap_next が立っている。"""
    e = setup(rules, {"hand": ["T001"]}, {"bz": ["T004"]})   # 手札があるので advance は自分の charge で止まる
    tgt = bz(e, 1, "T004")
    e.s.tasks.append(e._child([{"op": "tap", "select": {"zone": "bz", "owner": "opp",
                                                        "filter": {"types": ["creature"]}, "count": 1},
                                "no_untap_next": True}],
                              {"you": 0, "self": None, "vars": {}}))
    e.advance()
    assert e.s.cards[tgt].tapped and e.s.cards[tgt].no_untap_next


def test_enters_tapped_creature_enters_tapped(rules):
    """enters_tapped のクリーチャーは召喚するとタップ状態で出る。"""
    e = setup(rules, {"hand": ["T025"], "mana": ["T005", "T005"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T025")
    e.advance()
    c = bz(e, 0, "T025")
    assert e.s.cards[c].tapped


def test_force_battle_battles_chosen_creature(rules):
    """出た時に相手クリーチャーとバトルさせ、パワーの大きい側が残る。"""
    e = setup(rules, {"hand": ["T026"], "mana": ["T005"] * 3}, {"bz": ["T004"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T026")
    d = e.advance()                                         # 「バトルさせてもよい」の yes_no
    assert d["kind"] == "yes_no"
    e.answer([0])                                           # yes（対象は1体だけなので選択は自動）
    e.advance()
    assert "T026" in names(e, "bz", 0)                      # 5000 が残る
    assert names(e, "graveyard", 1) == ["T004"]             # 3000 は破壊される
