"""総合ゲームルール Ver.1.53 の条文ごとの準拠テスト。

コンボ探索で見つかる「勝ち筋」がエンジンのバグ由来にならないよう、勝敗に効く条文を最小の盤面で確かめる。
各テストの docstring の先頭に条文番号を書く。盤面用の架空カードは tests/rule_cards.yaml（R 始まり）。
"""
from pathlib import Path

import pytest
from conftest import answer, setup

from dmsim.defs import DATA, load_rules
from dmsim.defs import card_yaml_files  # noqa: E402
from dmsim.engine import Engine


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


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


# ---- 509.2 ブレイク数 / 609.9 置換後のイベント ----

def test_multiple_breaker_abilities_choose_one(rr):
    """509.2c W・ブレイカーとT・ブレイカーを同時に持つなら、どちらかの能力を選ぶ。W を選べば2つブレイクする。"""
    e = setup(rr, {"bz": ["R017"]}, {"shield": ["T001"] * 5})
    answer(e, "attack", "attack:R017:player")
    d = e.advance()
    assert d["kind"] == "choose_breaker" and d["player"] == 0
    assert keys(d) == ["breaks:2", "breaks:3"]      # 1つだけブレイクは選べない
    e.answer([0])
    d = e.advance()
    assert d["kind"] == "choose_shields" and d["min"] == d["max"] == 2


def test_single_breaker_ability_needs_no_choice(rr):
    """509.2b W・ブレイカー1つだけなら選択なしで2つブレイクする。"""
    e = setup(rr, {"bz": ["T005"]}, {"shield": ["T001"] * 5})
    answer(e, "attack", "attack:T005:player")
    d = e.advance()
    assert d["kind"] == "choose_shields" and d["max"] == 2


def test_replacement_events_apply_with_the_bundle(rr):
    """609.9 置換後のイベントは、置換されなかったイベントと同時（1つの束）に適用する。"""
    e = setup(rr, {"bz": ["T007", "T001"], "hand": ["R002"], "mana": ["T008"]})
    batches = []
    orig = e.apply_batch
    e.apply_batch = lambda evs: (batches.append([(x["to"], x["subject"][0]) for x in evs if x["ev"] == "move"]),
                                 orig(evs))[1]
    answer(e, "charge", "pass")
    answer(e, "main", "play:R002")
    answer(e, "choose_replacement", "replace:T007:0")
    e.advance()
    both = [b for b in batches if {"mana", "graveyard"} <= {z for z, _ in b}]
    assert len(both) == 1
    assert names(e, "mana", 0).count("T007") == 1


def test_103_initial_setup_and_first_turn(rules):
    """103.2/113.1/406.1/500.6: 双方の初期シールド5枚・初期手札5枚。先攻の第1ターンはドローしない。"""
    deck = ["T001"] * 20
    e = Engine.new_game(rules, [deck, deck], seed=3)
    for p in (0, 1):
        assert len(e.zlist("shield", p)) == 5 and len(e.zlist("hand", p)) == 5
        assert len(e.zlist("deck", p)) == 10
    e.advance()
    assert len(e.zlist("hand", 0)) == 5          # 先攻は第1ターンのドローなし


# ---- 801 進化クリーチャー ----

def _evolve_and_rebuild(rr, base_entered_this_turn: bool):
    """T002 の上に T017 で進化し、T017 だけを手札に戻して再構築する。(局面, 再構築後の T002 の cid, 進化したターン) を返す。"""
    e = setup(rr, {"bz": ["T002"], "hand": ["T017"], "mana": ["T001", "T001"]})
    base = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T002")
    answer(e, "charge", "pass")
    turn0 = e.s.turn
    if base_entered_this_turn:
        e.s.cards[base].entered_turn = e.s.turn      # このターンに出たクリーチャーを進化元にする
    answer(e, "main", "play:T017")
    e.advance()
    top = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T017")
    assert e._can_attack(top)                          # 801.3 進化クリーチャーは召喚酔いしない
    e.s.waiting = None
    run_ops(e, [{"op": "move", "select": {"ref": "self"}, "to": "hand", "reason": "return", "card_only": True}])
    e.s.tasks[-1]["env"]["self"] = e.s.ref(top)
    e.advance()
    return e, base, turn0


def test_801_4c_rebuilt_card_kept_from_turn_start_is_not_sick(rr):
    """801.4c ターンのはじめから進化クリーチャーの下にあったクリーチャーは、再構築されても新たに召喚酔いしない。"""
    e, base, turn0 = _evolve_and_rebuild(rr, base_entered_this_turn=False)
    assert e.s.cards[base].zone == "bz" and e.s.cards[base].entered_turn != turn0   # 攻撃できる（召喚酔いでない）


def test_801_4c_rebuilt_card_entered_this_turn_is_still_sick(rr):
    """801.4c ターンのはじめから下にあったのでなければ（このターンに出たクリーチャーを進化元にした場合）召喚酔いする。"""
    e, base, turn0 = _evolve_and_rebuild(rr, base_entered_this_turn=True)
    assert e.s.cards[base].zone == "bz" and e.s.cards[base].entered_turn == turn0   # このターンは召喚酔い


def _evolve_from_two(rr, tapped: tuple[bool, bool]):
    e = setup(rr, {"bz": ["T002", "T001"], "hand": ["R019"], "mana": ["T001", "T001"]})
    a, b = (next(c for c in e.bz_tops(0) if e.s.cards[c].defn == n) for n in ("T002", "T001"))
    answer(e, "charge", "pass")
    e.s.cards[a].tapped, e.s.cards[b].tapped = tapped
    answer(e, "main", "play:R019")
    d = e.advance()
    assert d["kind"] == "choose_evo_source"
    e.answer([0, 1])
    e.advance()
    top = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "R019")
    return e, top, a, b


def test_801_1b_evolution_can_stack_several_battle_zone_cards(rr):
    """801.1b 複数のカードを進化元にして出す場合、バトルゾーンの進化元もすべて下に重ねる。"""
    e, top, a, b = _evolve_from_two(rr, (False, False))
    assert sorted(e.s.cards[top].under) == sorted([a, b])
    assert [e.s.cards[c].zone for c in (a, b)] == ["bz", "bz"]
    assert e.bz_tops(0) == [top]


def test_801_2b_mixed_tapped_sources_make_a_tapped_evolution(rr):
    """801.2b タップ状態とアンタップ状態の進化元から進化したクリーチャーは、タップしてバトルゾーンに置かれる。"""
    for tapped in ((True, False), (False, True), (True, True)):
        e, top, a, b = _evolve_from_two(rr, tapped)
        assert e.s.cards[top].tapped, tapped
    e, top, a, b = _evolve_from_two(rr, (False, False))
    assert not e.s.cards[top].tapped


# ---- 113.6 効果によってシールドが手札に加えられる時の使用宣言 ----

def _shield_to_hand_by_effect(rr):
    e = setup(rr, {"hand": ["R020"], "mana": ["T001"], "shield": ["T018"] * 5}, {"bz": ["T001"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:R020")
    return e


def test_113_6_effect_moving_shield_to_hand_allows_strigger_declaration(rr):
    """113.6 ブレイクだけでなく効果でシールドが手札に加えられる時も、S・トリガーを宣言して使える。"""
    e = _shield_to_hand_by_effect(rr)
    d = e.advance()
    while d["kind"] != "declare_strigger":
        e.answer([0])
        d = e.advance()
    assert d["player"] == 0 and "strigger:T018:1" in keys(d)
    e.answer([keys(d).index("strigger:T018:1")])
    d = e.advance()
    while d is not None and d["kind"] != "attack" and d["kind"] != "main":
        e.answer([0])
        d = e.advance()
    assert "T001" not in names(e, "bz", 1)                   # 呪文側の効果で相手のクリーチャーが手札に戻った
    assert len(e.zlist("shield", 0)) == 4 and "T018" in names(e, "graveyard", 0)


def test_113_6_effect_moving_shield_to_hand_without_declaring_just_adds_it(rr):
    """113.6 宣言しなければ、シールドはそのまま手札に加わる（効果は起こらない）。"""
    e = _shield_to_hand_by_effect(rr)
    d = e.advance()
    while d["kind"] != "declare_strigger":
        e.answer([0])
        d = e.advance()
    e.answer([])
    e.advance()
    assert names(e, "hand", 0).count("T018") == 1 and len(e.zlist("shield", 0)) == 4
    assert names(e, "bz", 1) == ["T001"]


# ---- 113.2 シールドの束（シールド・プラス） ----

def _bundle(rr, extra_shield=("T018",) * 4):
    """シールド5枚のうち1つの下に山札の上から3枚を重ねた状態（束は1つのシールドと数える）。"""
    e = setup(rr, {"hand": ["R021"], "mana": ["T001"], "shield": ["T018"] * 5}, {"bz": ["T001"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:R021")
    d = e.advance()
    while d is not None and d["kind"] not in ("attack", "main"):
        e.answer([0])
        d = e.advance()
    return e


def test_113_2_bundle_counts_as_one_shield_but_cards_are_kept(rr):
    """113.2 重ねたカードの束は1つのシールドと数える。束のカードも持ち主のものとして保たれる。"""
    e = _bundle(rr)
    assert len(e.zlist("shield", 0)) == 5
    tops = [c for c in e.zlist("shield", 0) if e.s.cards[c].under]
    assert len(tops) == 1 and len(e.s.cards[tops[0]].under) == 3
    assert all(e.s.cards[u].zone == "shield" and e.s.cards[u].top_of == tops[0] for u in e.s.cards[tops[0]].under)


from conftest import find_option  # noqa: E402


def test_113_2_bundle_moves_together_to_hand_and_every_card_can_be_declared(rr):
    """束のシールドが効果で手札に加わる時は、束のすべてのカードが同時に手札に加わり、S・トリガーはどれも宣言できる。"""
    e = setup(rr, {"hand": ["R021", "R020"], "mana": ["T001", "T001"], "shield": ["T018"] * 3}, {"bz": ["T001"]}, filler="T018")
    answer(e, "charge", "pass")
    answer(e, "main", "play:R021")
    d = e.advance()
    while d["kind"] != "main":
        e.answer([0])
        d = e.advance()
    top = next(c for c in e.zlist("shield", 0) if e.s.cards[c].under)
    unders = list(e.s.cards[top].under)
    e.answer([find_option(d, "play:R020")])
    d = e.advance()
    while d["kind"] != "declare_strigger":
        e.answer([next((i for i, o in enumerate(d["options"]) if o["key"].startswith("shield")), 0)] if d["kind"] == "choose_shields" else [0])
        d = e.advance()
    assert len(d["options"]) == 4                               # 束の4枚すべてが宣言できる（T018 は S・トリガーを持つ）
    e.answer([])
    e.advance()
    assert all(e.s.cards[c].zone == "hand" for c in [top] + unders)
    assert len(e.zlist("shield", 0)) == 2


def test_loop_skeleton_distinguishes_bundle_contents_but_not_plain_shield_count(rr):
    """束の中身が違えば骨格は別（ループの判定に効く）。単独のシールドは従来どおり枚数だけ（counter）。"""
    from dmsim import loop
    e = _bundle(rr)
    h1, c1 = loop.abstract(e)
    top = next(c for c in e.zlist("shield", 0) if e.s.cards[c].under)
    u = e.s.cards[top].under[0]
    e.s.cards[u].defn = "T018"            # 束の中身のカードを入れ替える（内部状態の検査用）
    h2, _ = loop.abstract(e)
    assert h1 != h2
    assert c1["shield:0"] == 5            # 束は1つのシールド


def test_break_st_first_resolves_declared_s_trigger_before_following_step(rr):
    """S・トリガーは宣言後すぐ解決される。「その後」の処理（ドロー）はそれが終わってから行う。"""
    e = setup(rr, {"hand": ["R022"], "mana": ["T001"], "shield": ["R008"]}, {"bz": ["T001"], "shield": ["T018"] * 3}, filler="T018")
    seq = []
    orig = e._raw_move

    def spy(cid, to, *a, **k):
        c = e.s.cards[cid]
        if (c.owner, c.zone, to) == (1, "shield", "hand"):
            seq.append("opp_shield_broken_by_trigger")
        if (c.owner, c.zone, to) == (0, "deck", "hand"):
            seq.append("draw")
        return orig(cid, to, *a, **k)

    e._raw_move = spy
    answer(e, "charge", "pass")
    answer(e, "main", "play:R022")
    d = e.advance()
    while d is not None and d["kind"] not in ("attack", "main"):
        e.answer([0])
        d = e.advance()
    assert seq[:2] == ["opp_shield_broken_by_trigger", "draw"]
