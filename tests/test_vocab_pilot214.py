"""語彙パイロット第214弾: revenge_chance（リベンジ・チャンス）。

リベンジ・チャンスはイディオムで表せる（新規の能力語彙なし）:

- 手札の誘発 {kind: trigger, zone: hand, when: {event: turn_end}, if: 条件}
  ＋ 効果は may → play_free {select: {ref: self}}（アタック・チャンスや
  ニンジャ・ストライクと同じ自己無料召喚の形）
- 条件は既存の履歴・存在で書ける: exists（相手の大物がいる）、
  turn_count enter / draw（相手がそのターン出した／引いた数）

あわせて履歴カウンタに移動元ゾーンの修飾を足した:
{turn_count: {kind: shield_put, from: deck}} のように、移動で数える
kind は hist:<kind>_from_<zone> を読む（「山札からシールドゾーンに
加えた」を、手札から加えた場合と区別するため）。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T544", "T545", "T546", "T547", "T548", "T549", "T550", "T551")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def _in_bz(e, defn, ctrl):
    return any(e.s.cards[c].defn == defn and e.s.cards[c].controller == ctrl
               for c in e.zlist("bz", 0))


def _in_hand(e, defn, ctrl):
    return any(e.s.cards[c].defn == defn for c in e.zlist("hand", ctrl))


def _run(e, plays, yes=True, stop=None, limit=800):
    """ゲームを進める。plays は {player: [play キー]} で、提示されたら順に使う。
    yes_no（リベンジ・チャンスの may）は yes で答える。yes の提示を受けた
    プレイヤーの一覧を返す。"""
    plays = {p: list(v) for p, v in plays.items()}
    yes_seen = []
    for _ in range(limit):
        if stop and stop():
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        p = d.get("player")
        if d["kind"] == "yes_no":
            yes_seen.append(p)
            e.answer([0 if yes else 1])
        elif d["kind"] in ("main", "attack"):
            todo = plays.get(p) or []
            hit = next((k for k in todo if k in keys), None)
            if hit is not None:
                todo.remove(hit)
                e.answer([keys.index(hit)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return yes_seen


def _two_turns(e):
    """両者が1ターンずつ終えた目安（ターン番号が3以上）。"""
    return e.s.turn >= 3


def test_rc_exists_condition_fires(rules):
    # 相手にコスト9以上のクリーチャーがいれば、ターン終わりに無料召喚できる
    e = setup(rules, {"hand": ["T544"]}, {"bz": ["T201"]}, filler="T002")
    yes = _run(e, {}, stop=lambda: _in_bz(e, "T544", 0) or _two_turns(e))
    assert 0 in yes
    assert _in_bz(e, "T544", 0)


def test_rc_exists_condition_decline(rules):
    # 断れば手札に残る
    e = setup(rules, {"hand": ["T544"]}, {"bz": ["T201"]}, filler="T002")
    yes = _run(e, {}, yes=False, stop=lambda: _two_turns(e))
    assert 0 in yes
    assert _in_hand(e, "T544", 0) and not _in_bz(e, "T544", 0)


def test_rc_exists_condition_unmet(rules):
    # 相手に大物がいなければ提示されない
    e = setup(rules, {"hand": ["T544"]}, {}, filler="T002")
    yes = _run(e, {}, stop=lambda: _two_turns(e))
    assert 0 not in yes
    assert _in_hand(e, "T544", 0)


def test_rc_enter_count_condition(rules):
    # 相手がそのターン2体出したら提示される
    e = setup(rules, {"hand": ["T545"]},
              {"hand": ["T551", "T551"], "mana": ["T060", "T060"]}, filler="T002")
    yes = _run(e, {1: ["play:T551", "play:T551"]},
               stop=lambda: _in_bz(e, "T545", 0) or _two_turns(e))
    assert _in_bz(e, "T551", 1)   # 相手が2体出した前提の確認
    assert 0 in yes and _in_bz(e, "T545", 0)


def test_rc_enter_count_unmet(rules):
    # 1体だけなら提示されない
    e = setup(rules, {"hand": ["T545"]},
              {"hand": ["T551"], "mana": ["T060"]}, filler="T002")
    yes = _run(e, {1: ["play:T551"]}, stop=lambda: _two_turns(e))
    assert 0 not in yes
    assert _in_hand(e, "T545", 0)


def test_rc_shield_from_deck_condition(rules):
    # 相手が山札からシールドを加えたら提示される
    e = setup(rules, {"hand": ["T546"]},
              {"hand": ["T549"], "mana": ["T030", "T030"]}, filler="T002")
    yes = _run(e, {1: ["play:T549"]},
               stop=lambda: _in_bz(e, "T546", 0) or _two_turns(e))
    assert 0 in yes and _in_bz(e, "T546", 0)


def test_rc_shield_from_hand_does_not_count(rules):
    # 手札から加えたシールドは「山札から」ではないので数えない（from 修飾）
    e = setup(rules, {"hand": ["T546"]},
              {"hand": ["T548", "T002"], "mana": ["T030", "T030"]}, filler="T002")
    shields_before = len(e.zlist("shield", 1))
    yes = _run(e, {1: ["play:T548"]}, stop=lambda: _two_turns(e))
    assert len(e.zlist("shield", 1)) == shields_before + 1   # 加えた前提の確認
    assert 0 not in yes
    assert _in_hand(e, "T546", 0)


def test_rc_draw_count_condition(rules):
    # 相手がそのターン3枚引いたら（開始ドロー1＋呪文2）提示される
    e = setup(rules, {"hand": ["T547"]},
              {"hand": ["T550"], "mana": ["T030", "T030"]}, filler="T002")
    yes = _run(e, {1: ["play:T550"]},
               stop=lambda: _in_bz(e, "T547", 0) or _two_turns(e))
    assert 0 in yes and _in_bz(e, "T547", 0)


def test_rc_draw_count_unmet(rules):
    # 開始ドローだけ（1枚）では提示されない
    e = setup(rules, {"hand": ["T547"]}, {"mana": ["T030", "T030"]}, filler="T002")
    yes = _run(e, {}, stop=lambda: _two_turns(e))
    assert 0 not in yes
    assert _in_hand(e, "T547", 0)
