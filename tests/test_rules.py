"""総合ゲームルール Ver.1.53 の条文ごとの準拠テスト。

コンボ探索で見つかる「勝ち筋」がエンジンのバグ由来にならないよう、勝敗に効く条文を最小の盤面で確かめる。
各テストの docstring の先頭に条文番号を書く。盤面用の架空カードは tests/rule_cards.yaml（R 始まり）。
"""
from pathlib import Path

import pytest
from conftest import answer, setup

from dmsim.defs import DATA, load_rules


@pytest.fixture(scope="module")
def rr():
    return load_rules(sorted((DATA / "cards").glob("*.yaml")) + [Path(__file__).parent / "rule_cards.yaml"])


def names(e, z, p):
    return sorted(e.s.cards[c].defn for c in e.zlist(z, p))


def keys(d):
    return [o["key"] for o in d["options"]]


def run_ops(e, ops, you=0):
    """効果を1つ直接実行する（カードを介さずに条文の状況を作る）。"""
    e.s.tasks.append(e._child(ops, {"you": you, "self": None, "vars": {}}))


# ---- 104 勝利条件 / 703.4 状況起因処理 ----

def test_direct_attack_needs_unchanged_target(rr):
    """104.2a / 509.1 シールド0枚の相手への攻撃がブロックされたら（攻撃先が変わったら）勝利しない。"""
    e = setup(rr, {"bz": ["T005"]}, {"bz": ["T004"], "shield": []})
    answer(e, "attack", "attack:T005:player")
    answer(e, "block", "bz:T004:0")
    e.advance()
    assert e.s.result is None
    assert names(e, "graveyard", 0) == ["T005"] and names(e, "graveyard", 1) == ["T004"]   # 3000 同士で相打ち


def test_direct_attack_wins(rr):
    """104.2a / 509.1 / 703.4a ブロックされずシールド0枚ならダイレクトアタックで勝利。"""
    e = setup(rr, {"bz": ["T005"]}, {"bz": ["T004"], "shield": []})
    answer(e, "attack", "attack:T005:player")
    answer(e, "block", "no_block")
    assert e.advance() is None
    assert e.s.result == {"winner": 0, "reason": "direct_attack", "turn": 1}


def test_own_deck_out_stops_the_effect(rr):
    """104.2b / 703.4b 自分の効果で自分の山札が0枚になった瞬間に負け。効果の残り（2枚目のドロー）は行わない。"""
    e = setup(rr, {"hand": ["T003"], "mana": ["T003", "T003"]}, deck_left=[1, None])
    answer(e, "charge", "pass")
    hand = len(e.zlist("hand", 0))
    answer(e, "main", "play:T003")
    assert e.advance() is None
    assert e.s.result == {"winner": 1, "reason": "deck_out", "turn": 1}
    assert len(e.zlist("hand", 0)) == hand - 1 + 1


def test_both_decks_out_at_once_turn_player_loses(rr):
    """104.2b / 703.4b 両者の山札が同時に0枚になったら、ターン・プレイヤーの敗北とする。
    条文に明記はなく、プロジェクトの裁定（2026-10-24）。"""
    e = setup(rr, {"hand": ["R012"], "mana": ["T003"]}, deck_left=[1, 1])
    answer(e, "charge", "pass")
    answer(e, "main", "play:R012")
    assert e.advance() is None
    assert e.s.result == {"winner": 1, "reason": "deck_out", "turn": 1}


def test_each_player_draws_turn_player_first(rr):
    """114.2a 各プレイヤーが引く時は、ターン・プレイヤーが指定枚数を引いてから非ターン・プレイヤーが引く。
    先に引いたターン・プレイヤーの山札が尽きれば、その時点で負け（相手はまだ引いていない）。"""
    e = setup(rr, {}, {}, deck_left=[1, 1])
    run_ops(e, [{"op": "draw", "player": "each", "count": 1}])
    assert e.advance() is None
    assert e.s.result == {"winner": 1, "reason": "deck_out", "turn": 1}
    assert len(e.zlist("deck", 1)) == 1


def test_each_player_draws_count_each(rr):
    """114.2 / 114.2a 「各プレイヤーは2枚引く」= ターン・プレイヤー2回 → 非ターン・プレイヤー2回。"""
    e = setup(rr, {}, {})
    h0, h1 = len(e.zlist("hand", 0)), len(e.zlist("hand", 1))
    run_ops(e, [{"op": "draw", "player": "each", "count": 2}])
    e.advance()
    assert len(e.zlist("hand", 0)) == h0 + 2 and len(e.zlist("hand", 1)) >= h1 + 2


def test_deck_out_by_putting_under_a_creature(rr):
    """104.2b 山札の最後の1枚を（イベントを通さない処理で）クリーチャーの下に置いても、その瞬間に負け。
    同じターンのうちに続けて行動できてはいけない。"""
    e = setup(rr, {"hand": ["R011", "R011"], "mana": ["T001", "T001"]}, deck_left=[1, None])
    answer(e, "charge", "pass")
    answer(e, "main", "play:R011")
    assert e.advance() is None, "山札が0枚なのに次の行動を選べてしまう"
    assert e.s.result == {"winner": 1, "reason": "deck_out", "turn": 1}


def test_momentary_empty_deck_loses(rr):
    """104.2b 効果の途中で一瞬でも山札が0枚になれば負け。同じイベントの束で山札にカードが戻っても取り消されない。"""
    e = setup(rr, {"hand": ["T001"]}, deck_left=[1, None])
    top, h = e.zlist("deck", 0)[0], e.zlist("hand", 0)[0]
    e.s.tasks.append(e.ev_task([{"ev": "move", "subject": e.s.ref(top), "to": "graveyard", "reason": "put"},
                                {"ev": "move", "subject": e.s.ref(h), "to": "deck", "reason": "put"}]))
    assert e.advance() is None
    assert e.s.result == {"winner": 1, "reason": "deck_out", "turn": 1}


def test_power_zero_is_destroyed_mid_effect(rr):
    """703.4c / 111.2d パワー0以下は効果の解決中でもただちに破壊される。
    「その後、相手のクリーチャーがいなければ」の判定時点ではもう破壊されている。"""
    e = setup(rr, {"hand": ["R013"], "mana": ["T008"]}, {"bz": ["T001"]})
    answer(e, "charge", "pass")
    hand = len(e.zlist("hand", 0))
    answer(e, "main", "play:R013")
    e.advance()
    assert names(e, "graveyard", 1) == ["T001"]
    assert len(e.zlist("hand", 0)) == hand - 1 + 1       # 呪文 -1、ドロー +1


def test_power_zero_is_destroyed_without_a_following_event(rr):
    """703.4c 「出た時」のパワー低下の後、次のイベントを待たずに破壊される（次の行動を選ぶ時点で墓地にある）。"""
    e = setup(rr, {"hand": ["R014", "R014"], "mana": ["T008", "T008"]}, {"bz": ["T001"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:R014")
    d = e.advance()
    assert d["kind"] == "main" and d["player"] == 0
    assert names(e, "graveyard", 1) == ["T001"]


def test_power_zero_after_expiry_dies_in_that_turn(rr):
    """703.4c / 511.2 ターン終了時に修整が切れてパワー0以下になったら、そのターンのうちに破壊される
    （「自分のターン中に破壊された時」が誘発して解決される）。"""
    e = setup(rr, {"bz": ["R016"], "hand": ["T001"]})
    c = e.zlist("bz", 0)[0]
    for i, (p, dur) in enumerate([(-3000, "permanent"), (3000, "end_of_turn")]):
        e.s.seq += 1
        e.s.continuous.append({"id": e.s.seq, "mod": {"power": p}, "duration": dur, "controller": 0,
                               "affected": [e.s.ref(c)]})
    answer(e, "charge", "pass")
    hand = len(e.zlist("hand", 0))
    answer(e, "attack", "pass")
    d = e.advance()
    assert d["player"] == 1
    assert names(e, "graveyard", 0) == ["R016"]
    assert len(e.zlist("hand", 0)) == hand + 1


# ---- 101.5 / 609 置換効果 ----

def test_one_replacement_per_event_player_chooses(rr):
    """609.8 / 101.5b 同じプレイヤーの置換効果が複数あれば本人が1つ選ぶ。101.5 / 609.3 適用は1回だけ。"""
    e = setup(rr, {"bz": ["T007", "R003"], "hand": ["T011"], "mana": ["T005", "T005"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T011")
    answer(e, "choose_cards", "bz:T007:0")
    d = answer(e, "choose_replacement", "replace:R003:0")
    assert sorted(keys(d)) == ["decline", "replace:R003:0", "replace:T007:0"]
    e.advance()
    assert "T007" in names(e, "hand", 0)
    assert "T007" not in names(e, "mana", 0) and "T007" not in names(e, "graveyard", 0)


def test_turn_player_replacement_first(rr):
    """609.8 / 101.5b ターン・プレイヤーの置換効果が優先。強制なら非ターン・プレイヤーの置換は選べない。"""
    e = setup(rr, {"bz": ["R004"], "hand": ["T006"], "mana": ["T005"] * 3}, {"bz": ["T007"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T006")
    d = e.advance()
    assert not (d["kind"] == "choose_replacement" and d["player"] == 1)
    t007 = next(c for c in range(len(e.s.cards)) if e.s.cards[c].defn == "T007")
    assert e.s.cards[t007].zone == "deck" and e.zlist("deck", 1)[-1] == t007


def test_non_turn_player_replacement_after_decline(rr):
    """609.8 ターン・プレイヤーが任意の置換を使わなければ、非ターン・プレイヤーの置換効果が適用できる。"""
    e = setup(rr, {"bz": ["R003", "T001"], "hand": ["T011"], "mana": ["T005", "T005"]}, {"bz": ["R004"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T011")
    answer(e, "choose_cards", "bz:T001:0")
    answer(e, "choose_replacement", "decline")
    e.advance()
    t001 = next(c for c in e.zlist("deck", 0)[-1:])
    assert e.s.cards[t001].defn == "T001"
    assert "T001" not in names(e, "graveyard", 0)


def test_simultaneous_events_each_get_a_replacement(rr):
    """609.9 同時に起こる複数のイベントには、それぞれ別に置換効果を適用できる。"""
    e = setup(rr, {"bz": ["T007", "T007"], "hand": ["R002"], "mana": ["T008"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:R002")
    answer(e, "choose_replacement", "replace:T007:0")
    answer(e, "choose_replacement", "decline")
    e.advance()
    assert names(e, "mana", 0).count("T007") == 1 and names(e, "graveyard", 0).count("T007") == 1


def test_turn_player_decides_all_replacements_first(rr):
    """609.9a 同時に起こる複数のイベントでは、まずターン・プレイヤーが全イベント分の置換を決め、
    その後に非ターン・プレイヤーが決める（束の中で相手のイベントが先に並んでいても）。"""
    e = setup(rr, {"bz": ["T007"]}, {"bz": ["T007"]})
    mine, theirs = e.bz_tops(0)[0], e.bz_tops(1)[0]
    e.s.tasks.append(e.ev_task([{"ev": "move", "subject": e.s.ref(c), "to": "graveyard", "reason": "destroy"}
                                for c in (theirs, mine)]))
    d = e.advance()
    assert d["kind"] == "choose_replacement" and d["player"] == 0
    e.answer([keys(d).index("replace:T007:0")])
    d = e.advance()
    assert d["kind"] == "choose_replacement" and d["player"] == 1
    e.answer([keys(d).index("decline")])
    e.advance()
    assert names(e, "mana", 0) == ["T007"] and names(e, "graveyard", 1) == ["T007"]


# ---- 603 誘発型能力 ----

def test_leave_trigger_sees_only_itself_when_all_destroyed(rr):
    """603.5d 「クリーチャーが破壊された時」を持つクリーチャーが他と同時に破壊されたら、誘発は自身の1回だけ。"""
    e = setup(rr, {"bz": ["R001", "T001", "T001"], "hand": ["R002"], "mana": ["T008"]})
    answer(e, "charge", "pass")
    hand = len(e.zlist("hand", 0))
    answer(e, "main", "play:R002")
    e.advance()
    assert len(e.zlist("hand", 0)) == hand - 1 + 1


def test_trigger_per_destroyed_creature(rr):
    """603.2b 複数のクリーチャーが同時に破壊されたら、破壊された数だけ誘発する。"""
    e = setup(rr, {"bz": ["R001"]}, {"bz": ["T001", "T001"]})
    hand = len(e.zlist("hand", 0))
    run_ops(e, [{"op": "move", "select": {"zone": "bz", "owner": "opp", "count": "all"}, "to": "graveyard",
                 "reason": "destroy"}])
    d = e.advance()
    assert d["kind"] == "order_pending" and len(d["options"]) == 2
    e.answer([0])
    e.advance()
    assert len(e.zlist("hand", 0)) == hand + 2


def test_one_trigger_per_draw(rr):
    """114.2 / 603.2b 2枚引く = 1枚引くことを2回。「引いた時」は2回誘発する。"""
    e = setup(rr, {"hand": ["T003"], "mana": ["T003", "T003"]}, {"bz": ["R015"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T003")
    d = e.advance()
    assert d["kind"] == "order_pending" and d["player"] == 1
    assert len([p for p in e.s.pending if p["defn"] == "R015"]) == 2


# ---- 101.4 / 605.1 待機と解決の順 ----

def test_strigger_resolves_before_turn_player_effects(rr):
    """101.4a S・トリガーは（非ターン・プレイヤーのものでも）ターン・プレイヤーの待機効果より先に解決する。
    603.4 / 605.2a 誘発型能力の条件は解決時に確認する（攻撃クリーチャーはもういない）。"""
    e = setup(rr, {"bz": ["R006"]}, {"shield": ["T006"]})
    answer(e, "attack", "attack:R006:player")
    deck1 = len(e.zlist("deck", 1))
    answer(e, "declare_strigger", "strigger:T006")
    d = e.advance()
    assert d["player"] == 1                      # 相手のターンまで進んだ
    assert names(e, "graveyard", 0) == ["R006"]
    assert len(e.zlist("deck", 1)) == deck1 - 1   # 相手のドローの1枚だけ。R006 の墓地送りは行われない


def test_turn_player_effect_cuts_in(rr):
    """101.4c 非ターン・プレイヤーの効果の処理中にターン・プレイヤーの効果が誘発したら、
    非ターン・プレイヤーの残りの効果より先に処理する。"""
    e = setup(rr, {"bz": ["R015"]}, {"bz": ["T008", "T008"]})
    run_ops(e, [{"op": "move", "select": {"zone": "bz", "owner": "opp", "count": "all"}, "to": "graveyard",
                 "reason": "destroy"}])
    d = e.advance()
    assert d["kind"] == "order_pending" and d["player"] == 1
    e.answer([0])                                # T008 の1つ目: 相手が1枚引く → R015 が誘発
    d = e.advance()
    assert d["kind"] == "yes_no" and d["player"] == 0
    assert [p["defn"] for p in e.s.pending] == ["T008"]   # 相手の2つ目はまだ待機中


def test_effect_break_strigger_waits_for_the_effect(rr):
    """101.4d 効果の処理中に他の効果は割り込まない。呪文の効果でブレイクして出た S・トリガーは、
    その呪文の処理（「その後、〜」まで）が終わってから解決する。"""
    e = setup(rr, {"bz": ["T001"], "hand": ["R007"], "mana": ["T005"]}, {"shield": ["T006"]})
    answer(e, "charge", "pass")
    hand = len(e.zlist("hand", 0))
    answer(e, "main", "play:R007")
    answer(e, "declare_strigger", "strigger:T006")
    e.advance()
    assert len(e.zlist("hand", 0)) == hand - 1 + 2   # 呪文の残りでクリーチャーがいたので2枚引けた
    assert names(e, "graveyard", 0) == ["R007", "T001"]   # その後 S・トリガーで破壊


def test_strigger_inside_strigger_resolves_first(rr):
    """101.4g S・トリガーの解決中にブレイクされて新たに待機した S・トリガーは、すでに待機していた効果より先に、
    その場で解決する。"""
    e = setup(rr, {"bz": ["T005"], "shield": ["T006"]}, {"bz": ["T001", "T001"], "shield": ["R008", "R009"]})
    answer(e, "attack", "attack:T005:player")    # W・ブレイカーで2枚（シールドは2枚なので選択なし）
    d = e.advance()
    assert d["kind"] == "declare_strigger"
    e.answer([0, 1])
    answer(e, "order_pending", "pending:strigger:R008:-1")
    answer(e, "declare_strigger", "strigger:T006")   # R008 のブレイクで自分のシールド T006 が手札へ
    d = e.advance()
    assert d["kind"] == "choose_cards" and d["player"] == 0     # T006 の破壊対象を選ぶ（R009 より先）
    assert [p["defn"] for p in e.s.pending] == ["R009"]


def test_strigger_creature_etb_is_a_separate_effect(rr):
    """112.3a クリーチャーの S・トリガーは召喚までが能力。「出た時」は別の効果として待機し、
    残りの S・トリガーが先に解決する（101.4a）。"""
    e = setup(rr, {"bz": ["T005"]}, {"shield": ["R010", "T006"]})
    answer(e, "attack", "attack:T005:player")
    d = e.advance()
    assert d["kind"] == "declare_strigger"
    e.answer([0, 1])
    answer(e, "order_pending", "pending:strigger:R010:-1")
    d = e.advance()
    assert d["kind"] == "yes_no" and d["player"] == 1           # R010 の「出た時」
    assert names(e, "graveyard", 0) == ["T005"]                 # T006 はもう解決している


def test_both_players_cards_enter_turn_player_first(rr):
    """114.2a / 409.1e 両プレイヤーのカードを1枚ずつバトルゾーンに出す時は、ターン・プレイヤーのカードが先。"""
    e = setup(rr, {}, {}, filler="T001")
    e.s.active = 1
    run_ops(e, [{"op": "move", "select": {"zone": "deck", "owner": "any", "from_top": 1}, "to": "bz",
                 "reason": "put"}])
    e.advance()
    first, second = sorted(e.bz_tops(), key=lambda c: e.s.cards[c].entered_seq)
    assert e.s.cards[first].owner == 1 and e.s.cards[second].owner == 0
