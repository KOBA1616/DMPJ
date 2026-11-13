"""後戻りできない設計判断の検証テスト。各テストの docstring に対応する条文を書く。"""
import random

from conftest import answer, setup

from dmsim import Engine
from dmsim.engine.loop import LoopDetector, fast_forward, verify
from dmsim.engine.play import random_policy, replay, run


def zone_names(e, z, p):
    return sorted(e.s.cards[c].defn for c in e.zlist(z, p))


def test_object_generation(rules):
    """400.5 移動したカードは新しいオブジェクト。古い参照 [cid, gen] は無効になる。"""
    e = setup(rules, {"hand": ["T001"]})
    cid = e.zlist("hand", 0)[0]
    old = e.s.ref(cid)
    e._raw_move(cid, "graveyard")
    assert not e.s.alive(old) and e.s.alive(e.s.ref(cid))


def test_replay_is_deterministic(rules):
    """シード＋選択ログで完全に同じ対戦が再現できる。"""
    ids = list(rules.cards)
    deck = [ids[i % len(ids)] for i in range(40)]
    for seed in range(10):
        e = Engine.new_game(rules, [deck, deck], seed)
        rng = random.Random(seed)
        run(e, [random_policy(rng), random_policy(rng)])
        assert replay(rules, [deck, deck], seed, e.log).s.digest() == e.s.digest()


def test_state_clone_mid_decision(rules):
    """決定待ちの途中で state を複製し、別々に進められる（ISMCTS 用）。"""
    e = setup(rules, {"hand": ["T003"], "mana": ["T003", "T003"]})
    answer(e, "charge", "pass")
    e2 = e.clone()
    answer(e, "main", "play:T003")
    e.advance()
    assert len(e.zlist("hand", 0)) == 2 and len(e2.zlist("hand", 0)) == 1


def test_replacement_applies_and_blocks_destroyed_trigger(rules):
    """609.4 置換されたイベントは起こったことにならない（「破壊された時」は誘発しない, 603.2d）。"""
    e = setup(rules, {"bz": ["T007"], "hand": ["T011"], "mana": ["T005", "T005"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T011")
    answer(e, "choose_replacement", "replace:T007:0")
    d = e.advance()
    assert d["kind"] == "choose_shields"
    assert zone_names(e, "mana", 0) == ["T005", "T005", "T007"]
    assert e.s.pending == []


def test_replacement_declined(rules):
    e = setup(rules, {"bz": ["T007"], "hand": ["T011"], "mana": ["T005", "T005"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T011")
    answer(e, "choose_replacement", "decline")
    e.advance()
    assert "T007" in zone_names(e, "graveyard", 0)


def test_leave_trigger_uses_last_known_info(rules):
    """603.5c/d 離れた時の誘発は直前の状態で判定する。"""
    e = setup(rules, {"bz": ["T008"], "hand": ["T011"], "mana": ["T005", "T005"]})
    answer(e, "charge", "pass")
    hand_before = len(e.zlist("hand", 0))
    answer(e, "main", "play:T011")
    e.advance()        # 相手のシールド選択
    e.answer([0])
    e.advance()
    # 呪文が手札から出て -1、破壊時の誘発で +1
    assert len(e.zlist("hand", 0)) == hand_before


def test_deck_out_is_immediate(rules):
    """104.2b / 703.4b 効果の途中でも山札が0枚になった瞬間に敗北。"""
    e = setup(rules, {"hand": ["T012"], "mana": ["T003"]}, {}, deck_left=[None, 1])
    answer(e, "charge", "pass")
    answer(e, "main", "play:T012")
    assert e.advance() is None
    assert e.s.result["winner"] == 0 and e.s.result["reason"] == "deck_out"


def test_pending_order_is_a_decision(rules):
    """101.4a 同時に待機した自分の効果は、ターン・プレイヤーが好きな順で解決する。"""
    e = setup(rules, {"bz": ["T010"], "hand": ["T009"], "mana": ["T003"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T009")
    d = e.advance()
    assert d["kind"] == "order_pending"
    assert sorted(o["key"] for o in d["options"]) == ["pending:normal:T009:0", "pending:normal:T010:0"]


def test_strigger_from_attack(rules):
    """509.5 / 113.6 ブレイク → S・トリガー宣言 → 手札へ → コストなしで唱える。"""
    e = setup(rules, {"bz": ["T005"]}, {"shield": ["T006"] * 5})
    # 手札が空なのでマナチャージとメインは選択肢が1つ（pass）しかなく、決定は出ない
    answer(e, "attack", "attack:T005:player")
    d = e.advance()
    assert d["kind"] == "choose_shields" and d["min"] == d["max"] == 2   # W・ブレイカー
    e.answer([0, 1])
    d = e.advance()
    assert d["kind"] == "declare_strigger" and d["player"] == 1
    e.answer([0])
    e.advance()
    assert "T005" in zone_names(e, "graveyard", 0)
    assert zone_names(e, "graveyard", 1) == ["T006"]
    assert len(e.zlist("shield", 1)) == 3


def test_two_card_loop_is_stocked_and_wins(rules):
    """ストック: 同じ骨格に戻る行動列を検出し、Δ×N で相手の山札切れ勝ちを証明する。"""
    e = setup(rules, {"bz": ["T010"], "hand": ["T009"], "mana": ["T003"]})
    answer(e, "charge", "pass")
    det = LoopDetector(me=0)
    cert = None
    for _ in range(4):
        d = e.advance()
        assert d["kind"] == "main"
        cert = det.observe(e)
        if cert:
            break
        e.answer([[o["key"] for o in d["options"]].index("play:T009")])
        answer(e, "order_pending", "pending:normal:T010:0")
        answer(e, "yes_no", "yes")
        e.advance()   # 残った T009 の誘発（相手の山札を削る）は自動で解決される
    assert cert is not None
    assert cert.delta == {"deck:1": -1, "graveyard:1": 1}
    assert cert.limit == float("inf") and cert.win_by == "opp_deck_out"
    assert verify(e, cert, times=3).verified == 3
    fast_forward(e, cert, cert.needed)
    assert e.s.result == {"winner": 0, "reason": "deck_out", "turn": 1}


def test_new_op_is_added_without_touching_the_engine(rules):
    """拡張ポイント: op を registry に登録すれば、カードデータからそのまま使える。"""
    from dmsim.cards.defs import expand_ops
    from dmsim.engine.registry import OPS, op

    if "gain_mana_from_top" not in OPS:
        @op("gain_mana_from_top")
        def _gain(eng, t, o, env):
            return OPS["move"](eng, t, {"select": {"zone": "deck", "owner": "you", "from_top": o["count"]},
                                        "to": "mana", "reason": "put"}, env)
    ops = expand_ops([{"op": "gain_mana_from_top", "count": 2}], rules.macros, "test")
    e = setup(rules, {})
    e.s.tasks.append(e._child(ops, {"you": 0, "self": None, "vars": {}}))
    e.advance()
    assert len(e.zlist("mana", 0)) == 2


def test_state_clone_matches_deepcopy_and_is_independent(rules):
    import copy
    from dmsim.engine.play import default_decks
    e = Engine.new_game(rules, [default_decks(rules, "dm")[0], ["T001"] * 40], 3, 0)
    for _ in range(6):
        d = e.advance()
        if d is None:
            break
        e.answer([0])
    c = e.s.clone()
    assert c.to_json() == e.s.to_json() == copy.deepcopy(e.s).to_json()
    c.cards[0].under.append(99)
    c.zones["deck"][0].reverse()
    c.tasks.append({"t": "x"})
    assert e.s.cards[0].under == [] and e.s.digest() != c.digest()
