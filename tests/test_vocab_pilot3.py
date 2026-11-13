"""語彙パイロット第3弾（2026-10-30）の検証。

- キーワード freeze: 「相手プレイヤーを攻撃してブロックされなかった時」= break イベントの発生源が自分
  （rejects: freeze）
- subject フィルタの式評価: 誘発の対象条件でも cost_ge 等に式が書ける
  （「相手のマナゾーンの枚数よりコストが大きいクリーチャーが出た時」。rejects: cost_gt_count / cost_lt_count）
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
        if pred():
            return
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert pred()


def test_freeze_taps_and_freezes_after_unblocked_attack(rules):
    """ブロックされなかった攻撃でシールドをブレイクすると、フリーズで相手クリーチャーをタップ+凍結できる。"""
    e = setup(rules, {"bz": ["T034"]}, {"bz": ["T004"], "shield": ["T001"] * 5})
    tgt = bz(e, 1, "T004")
    answer(e, "attack", "attack:T034:player")
    answer(e, "block", "no_block")               # ブロックしない → シールドがブレイクされ、フリーズが誘発する
    advance_until(e, lambda: e.s.cards[tgt].tapped)
    # フリーズ解決の流れで相手のターン開始まで進んでいる: アンタップ判定は終わっていて、
    # タップしたままで印は消費されている（= 次の相手のアンタップを1回飛ばした）
    assert e.s.active == 1 and e.s.cards[tgt].tapped and not e.s.cards[tgt].no_untap_next
    turn = e.s.turn
    advance_until(e, lambda: e.s.active == 1 and e.s.turn > turn and e.s.waiting and e.s.waiting["kind"] == "charge")
    assert not e.s.cards[tgt].tapped             # その次の相手ターン開始では通常どおりアンタップする


def test_subject_filter_expr_cost_lt_graveyard_count(rules):
    """誘発の subject フィルタで「コストが自分の墓地の枚数より小さい」を式（cost_le に sum）で判定できる。

    cost_gt_count（「マナの枚数よりコストが大きい」）も同じ仕組みで、cost_ge に {sum: [count, 1]} を渡す。
    """
    from dmsim.cards.defs import load_tables, parse_card
    card = {"id": "TX01", "name": "試験用門番", "types": ["creature"], "civs": ["light"], "cost": 2,
            "power": 1000, "races": ["テスト"],
            "abilities": [{"kind": "trigger",
                           "when": {"event": "move", "to": "bz",
                                    "subject": {"owner": "opp", "filter": {"types": ["creature"],
                                                "cost_le": {"sum": [{"count": {"zone": "graveyard", "owner": "you"}}, -1]}}}},
                           "effect": [{"op": "draw", "count": 1}]}]}
    tables = load_tables()
    rules.cards["TX01"] = parse_card(card, tables, where="TX01")
    # 自分の墓地5枚 → コスト4以下が対象。コスト3の T005 は誘発し、コスト5の T019 は誘発しない
    e = setup(rules, {"bz": ["TX01"], "graveyard": ["T001"] * 5},
              {"hand": ["T005", "T019"], "mana": ["T005", "T008", "T001", "T001", "T001"]})
    h0 = len(e.zlist("hand", 0))
    advance_until(e, lambda: e.s.active == 1 and e.s.waiting and e.s.waiting["kind"] == "main")
    answer(e, "main", "play:T005")
    advance_until(e, lambda: len(e.zlist("hand", 0)) == h0 + 1)   # 誘発して1枚引いた
    turn = e.s.turn
    advance_until(e, lambda: e.s.active == 1 and e.s.turn > turn and e.s.waiting and e.s.waiting["kind"] == "main")
    h_before = len(e.zlist("hand", 0))
    answer(e, "main", "play:T019")
    advance_until(e, lambda: e.s.waiting and e.s.waiting["kind"] == "attack" and e.s.active == 1)
    assert len(e.zlist("hand", 0)) == h_before                     # 誘発していない
