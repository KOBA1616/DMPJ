"""《切札混成 ドギラダンテ刈》: EXライフ・ファイナル革命（そのターン1度）・「コスト７以下のクリーチャーを出せない」。"""
from conftest import answer, setup

from test_real_cards import bz, keys
from test_real_cards_combo import drive, names

DOG = "dm26ex4-sec015"
BOL = "dm24ex4-015"      # 光/火の多色ドラゴン（革命チェンジの元になる）
SAGA = "dm22ex2-021"     # 多色・コスト3


def run_ops(e, ops, you=0):
    e.s.tasks.append(e._child(ops, {"you": you, "self": None, "vars": {}}))


def revolution(rules, mark=False, opp_hand=(), mana=(SAGA,)):
    """ボルメテウスで攻撃して革命チェンジ。手札に出す多色カードは、マナゾーンのサガ。"""
    e = setup(rules, {"bz": [BOL], "hand": [DOG], "mana": list(mana)}, {"bz": ["dm01-080"], "hand": list(opp_hand)})
    answer(e, "charge", "pass")
    answer(e, "attack", f"attack:{BOL}:player")
    answer(e, "declare_attack", f"declare:{DOG}:2")
    if mark:
        e.s.turn_counters["final_revolution"] = 1
    return e


def settle(e, saga_to_bz=True):
    """order_pending と play_free の選択を済ませて、シールド選択（ブレイク）まで進める。"""
    return drive(e, lambda e, d: d["kind"] == "choose_shields",
                 pick=lambda d: next((i for i, k in enumerate(keys(d)) if k.startswith("hand:T001")), None))


def after_break(e, ops):
    """ブレイクするシールドを選んだあとで、ops を先に解決する（局面を作るためだけの割り込み）。"""
    d = e.advance()
    assert d["kind"] == "choose_shields"
    e.answer(list(range(d["min"])))
    run_ops(e, ops)
    e.advance()


def test_ex_life_shield_is_made_when_it_enters(rules):
    e = revolution(rules, mana=())
    before = len(e.zlist("shield", 0))
    settle(e)
    assert bz(e, 0, DOG) is not None and BOL in names(e, "hand", 0)      # 入れ替わった
    assert len(e.zlist("shield", 0)) == before + 1                        # 山札の上1枚がシールドに
    ex = [c for c in e.zlist("shield", 0) if e.s.cards[c].exlife_of is not None]
    assert len(ex) == 1 and e.s.alive(e.s.cards[ex[0]].exlife_of) and e.s.cards[ex[0]].exlife_of[0] == bz(e, 0, DOG)


def test_final_revolution_draws_and_plays_multicolor_from_mana(rules):
    e = revolution(rules)
    settle(e)
    assert SAGA in names(e, "bz", 0)                                      # マナのサガをコストを支払わずに出した
    assert e.s.turn_counters["final_revolution"] == 1


def test_final_revolution_draws_one(rules):
    e = revolution(rules, mana=())
    hand = len(e.zlist("hand", 0))
    settle(e)
    assert len(e.zlist("hand", 0)) == hand + 1 - 1 + 1                    # ドギラダンテが出て、ボルメテウスが戻り、1枚引く


def test_final_revolution_only_once_per_turn(rules):
    e = revolution(rules, mark=True)
    hand = len(e.zlist("hand", 0))
    settle(e)
    assert SAGA not in names(e, "bz", 0)                                  # 他のファイナル革命を使っていたので何もしない
    assert len(e.zlist("hand", 0)) == hand                                # ドギラダンテが出て、ボルメテウスが戻っただけ（ドローなし）


def test_ex_life_replaces_leaving_and_is_used_up(rules):
    e = revolution(rules, mana=())
    settle(e)
    dog = bz(e, 0, DOG)
    destroy = [{"op": "move", "select": {"zone": "bz", "owner": "you", "filter": {"name": "切札混成 ドギラダンテ刈"}},
                "to": "graveyard", "reason": "destroy"}]
    gy = len(e.zlist("graveyard", 0))
    after_break(e, destroy)
    assert bz(e, 0, DOG) == dog                                           # 離れない
    assert len(e.zlist("graveyard", 0)) == gy + 1                         # かわりにEXライフシールドが墓地へ
    assert not [c for c in e.zlist("shield", 0) if e.s.cards[c].exlife_of is not None]


def test_ex_life_second_destroy_leaves(rules):
    e = revolution(rules, mana=())
    settle(e)
    destroy = {"op": "move", "select": {"zone": "bz", "owner": "you", "filter": {"name": "切札混成 ドギラダンテ刈"}},
               "to": "graveyard", "reason": "destroy"}
    after_break(e, [destroy, destroy])                                    # 1回目はEXライフシールド、2回目で離れる
    assert DOG in names(e, "graveyard", 0)


def test_breaking_ex_life_shield_keeps_creature(rules):
    e = revolution(rules)
    settle(e)
    ex = next(c for c in e.zlist("shield", 0) if e.s.cards[c].exlife_of is not None)
    run_ops(e, [{"op": "move", "select": {"exlife_of": "self"}, "to": "hand", "reason": "break"}])
    # self=None の直接実行なので紐付けは辿れない。ブレイク相当は shield から手札へ動かして確認する
    e.s.tasks.pop()
    e._push(e.ev_task({"ev": "move", "subject": e.s.ref(ex), "to": "hand", "reason": "break"}))
    e.advance()
    assert bz(e, 0, DOG) is not None


def test_opponent_cannot_enter_cost_7_or_less_this_turn(rules):
    e = revolution(rules, opp_hand=["dm01-080", "dm22ex1-007"])
    cheap = next(c for c in e.zlist("hand", 1) if e.s.cards[c].defn == "dm01-080")
    big = next(c for c in e.zlist("hand", 1) if e.s.cards[c].defn == "dm22ex1-007")
    assert e.permits(cheap, "enter_bz")
    settle(e)
    assert not e.permits(cheap, "enter_bz")                               # コスト3
    assert e.permits(big, "enter_bz") == (e.chars(big)["cost"] > 7)       # 超神星DOOM・ドラゲリオンはコスト7以下かで決まる
    # 効果で出そうとしても出ない
    run_ops(e, [{"op": "move", "select": {"zone": "hand", "owner": "opp", "filter": {"name": "アクア・ハルカス"}},
                 "to": "bz", "reason": "put"}], you=0)
    e.advance()
    assert "dm01-080" in names(e, "hand", 1)


def test_multicolor_creatures_get_speed_attacker(rules):
    e = revolution(rules)
    settle(e)
    assert e.permits(bz(e, 0, DOG), "attack_summoning_sick")
    assert e.permits(bz(e, 0, SAGA), "attack_summoning_sick")
