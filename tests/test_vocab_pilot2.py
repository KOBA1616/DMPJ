"""語彙パイロット第2弾（2026-10-30）の検証。

- once_per_turn: 「各ターンに一度」の誘発ゲート（rejects: once_per_turn_trigger）
- first_time: 「各ターン、はじめて〜した時」の誘発ゲート（rejects: first_time_per_turn_trigger）
- civ_count 式: カード群にある文明の種類数（rejects: civ_count / civilization_count）
- アンタップの2文型の区別:
  A型「次の相手のターンのはじめにアンタップしない」= tap の no_untap_next（第1弾。対象の次のアンタップを必ず1回飛ばす）
  B型「次の自分のターンのはじめまでアンタップしない」= tap + modify {deny: [untap_at_start], duration: until_next_own_turn_start}
    （自分の次のターン開始で期限が切れる期限型。相手対象では間の相手のアンタップを1回飛ばすが、
      自分対象では次の自分のターン開始で切れているのでアンタップする = A型と異なる）
"""
from conftest import answer, setup


def bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def advance_until(e, pred, limit=200):
    for _ in range(limit):
        if pred():
            return
        d = e.advance()
        if d is None:
            break
        if pred():      # advance で来た Decision 自体が pred を満たすなら、答えずに返す
            return
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert pred()


def until_decision(e, kind, player=None, min_turn=0):
    """指定 kind の Decision が来るまで進める（step 名ではなく実際の決定で判定する）。"""
    advance_until(e, lambda: e.s.waiting is not None and e.s.waiting["kind"] == kind
                  and (player is None or e.s.waiting["player"] == player) and e.s.turn >= min_turn)


def test_once_per_turn_draws_only_once(rules):
    """同じターンに自分のクリーチャーが2体出ても、once_per_turn の誘発は1回だけ。次のターンにはまた誘発する。"""
    e = setup(rules, {"bz": ["T027"], "hand": ["T001", "T001"], "mana": ["T001"] * 6})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T001")            # 1体目: ドローが誘発する
    until_decision(e, "main", player=0)
    assert len(e.zlist("hand", 0)) == 2       # 使った1枚がドローで戻った
    answer(e, "main", "play:T001")            # 2体目: もう誘発しない
    until_decision(e, "attack", player=0)
    assert len(e.zlist("hand", 0)) == 1       # ドロー無しで1枚減ったまま
    # 次の自分のターン: 手札のクリーチャーを出すとまたドローする
    until_decision(e, "main", player=0, min_turn=3)
    h = len(e.zlist("hand", 0))
    answer(e, "main", "play:T001")
    until_decision(e, "main", player=0)
    assert len(e.zlist("hand", 0)) == h       # 使った分がドローで戻った


def test_first_time_attack_two_copies_both_trigger_once(rules):
    """「はじめて攻撃する時」は出来事の最初の発生を見る: 2コピーとも最初の攻撃で誘発し、2回目の攻撃では誘発しない。"""
    e = setup(rules, {"bz": ["T028", "T028", "T005", "T001"]}, {"shield": ["T001"] * 5})
    h0 = len(e.zlist("hand", 0))
    answer(e, "attack", "attack:T005:player")
    advance_until(e, lambda: len(e.zlist("hand", 0)) == h0 + 2)   # 最初の攻撃: 2コピーとも誘発
    until_decision(e, "attack", player=0)
    answer(e, "attack", "attack:T001:player")
    until_decision(e, "charge", player=1)
    assert len(e.zlist("hand", 0)) == h0 + 2  # 2回目の攻撃: 誘発しない


def test_civ_count_draw_counts_distinct_civs(rules):
    """マナの文明の種類数だけ引く（多色は持つ文明をすべて数える: 自然＋光/水 = 3種類）。"""
    e = setup(rules, {"hand": ["T029"], "mana": ["T001", "T030", "T001"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T029")
    e.advance()
    assert len(e.zlist("hand", 0)) == 3


def test_civ_count_power_scales_with_distinct_civs(rules):
    """常在型のパワー修整でも civ_count が使える（マナの文明ひとつにつき+4000）。"""
    e = setup(rules, {"bz": ["T031"], "mana": ["T001", "T030"]})
    c = bz(e, 0, "T031")
    assert e.chars(c)["power"] == 1000 + 4000 * 3   # 自然・光・水の3種類


def test_untap_b_type_opponent_skips_once_and_expires_at_own_next_start(rules):
    """B型（期限型）: 相手ターン開始ではまだ期限が残っていてアンタップせず、自分の次のターン開始で期限が切れ、その次の相手ターン開始でアンタップする。"""
    e = setup(rules, {"hand": ["T032"], "mana": ["T003"]}, {"bz": ["T004"]})
    tgt = bz(e, 1, "T004")
    answer(e, "charge", "pass")
    answer(e, "main", "play:T032")
    d = e.advance()                                   # 相手ターン開始のアンタップ判定は終わっている
    assert e.s.active == 1 and d["kind"] == "charge"
    assert e.s.cards[tgt].tapped                     # アンタップしていない
    assert any(c["duration"] == "until_turn_start:0" for c in e.s.continuous)   # 期限はまだ残っている
    turn1 = e.s.turn
    advance_until(e, lambda: e.s.active == 0 and e.s.turn > turn1 and e.s.step == "charge")
    assert not any(c["duration"] == "until_turn_start:0" for c in e.s.continuous)  # 自分のターン開始で期限切れ
    advance_until(e, lambda: e.s.active == 1 and e.s.turn > turn1 and e.s.step == "charge")
    assert not e.s.cards[tgt].tapped                  # 今度はアンタップする


def test_untap_b_type_own_creature_untaps_at_own_next_start(rules):
    """B型を自分のクリーチャーに使うと、次の自分のターン開始では期限が切れているのでアンタップする（A型=no_untap_next との違い）。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T033"], "mana": ["T003", "T003"]})
    tgt = bz(e, 0, "T001")
    answer(e, "charge", "pass")
    answer(e, "main", "play:T033")
    e.advance()
    assert e.s.cards[tgt].tapped
    turn0 = e.s.turn
    until_decision(e, "charge", player=0, min_turn=turn0 + 2)
    assert not e.s.cards[tgt].tapped                  # 期限切れ → 通常どおりアンタップした
