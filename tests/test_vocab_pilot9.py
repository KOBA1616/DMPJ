"""語彙パイロット第9弾（2026-10-31）の検証。

mod `cost_may {amount, once?, min?}`（rejects: optional_cost_reduction の常在型）:
他のカードの常在型が「自分の〜の召喚コストをN少なくしてもよい」を与える。
使うかどうかはプレイのたびに発生源ごとに選び、once なら発生源ごとにターン中1回まで。
"""
from conftest import answer, find_option, setup


def play_with_choice(e, key, choice):
    """play を選び、cost_may の確認（reduce / normal）が出たら choice で答える。
    カードが場に出たら止める。確認が出たかどうかを返す。"""
    defn = key.split(":")[1]
    d = e.advance()
    assert d is not None and d["kind"] == "main"
    before = len([c for c in e.bz_tops(0) if e.s.cards[c].defn == defn])
    e.answer([find_option(d, key)])
    seen = False
    for _ in range(10):
        if len([c for c in e.bz_tops(0) if e.s.cards[c].defn == defn]) > before:
            break
        d = e.advance()
        if d is None or d["kind"] == "main":   # メインに戻ったらこのプレイは終わっている
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_cards" and "reduce" in keys:
            seen = True
            e.answer([find_option(d, choice)])
        elif d["kind"] == "pay_mana":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return seen


def test_cost_may_once_per_turn(rules):
    e = setup(rules, {"bz": ["T044"], "hand": ["T001", "T001"],
                      "mana": ["T001", "T001", "T001"]}, {})
    answer(e, "charge", "pass")
    # 1体目: 軽減の確認が出て、使うと1マナで召喚できる
    assert play_with_choice(e, "play:T001", "reduce") is True
    assert len([c for c in e.bz_tops(0) if e.s.cards[c].defn == "T001"]) == 1
    # 2体目: once を使い切ったので確認は出ず、通常コスト（残り2マナ）で召喚する
    assert play_with_choice(e, "play:T001", "reduce") is False
    assert len([c for c in e.bz_tops(0) if e.s.cards[c].defn == "T001"]) == 2
    assert all(e.s.cards[c].tapped for c in e.s.zones["mana"][0])


def test_cost_may_decline_pays_full(rules):
    e = setup(rules, {"bz": ["T044"], "hand": ["T001"], "mana": ["T001", "T001"]}, {})
    answer(e, "charge", "pass")
    assert play_with_choice(e, "play:T001", "normal") is True
    assert len([c for c in e.bz_tops(0) if e.s.cards[c].defn == "T001"]) == 1
    assert all(e.s.cards[c].tapped for c in e.s.zones["mana"][0])   # 2マナとも使った
