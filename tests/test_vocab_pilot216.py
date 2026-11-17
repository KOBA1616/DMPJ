"""語彙パイロット第216弾: final_declaration（終極宣言）のゲート。

公式Q&A（dm.takaratomy.co.jp/rule/qa/44220）: 「終極宣言」はプレイヤーごとに
ゲーム中一度だけ。どのカードの終極宣言を使っても、その後は同プレイヤーの
他の終極宣言も使えない。効果を何も使わなかった（使わないを選んだ）場合は
消費されず、次の自分のターンのはじめに再びトリガーする。相手は独立に一度使える。

ゲートの形（イディオム）:
  trigger {when: {event: turn_start, subject: self},
           if: {not: {marked: {name: final_declaration, scope: game}}},
           effect: [if {not marked} then [may [<効果>, mark scope: game]]]}
  内側の if は、複数の終極宣言が同じターン開始に同時トリガーした時に、
  先に使った方で印が立ち、後の方が静かに解決するための再確認。

あわせて基盤の変更: mark の scope: game はプレイヤーごとに印を分ける
（_mark_key が名前＋プレイヤー番号にする）。使用履歴は各プレイヤーのもの
であり、相手の使用で自分の分が消費されることはない。

検証は山札の減り具合の相対比較で行う（宣言ドロー2枚ぶんの差だけを見る）。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T555", "T556")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def _play(e, script, turns=5, limit=4000):
    """yes_no（終極宣言の may）に script の順（True=使う）で答えながら進める。
    yes_no の記録 [(turn, active, player)] を返す。"""
    logs = []
    answers = list(script)
    for _ in range(limit):
        if e.s.turn > turns:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "yes_no":
            logs.append((e.s.turn, e.s.active, d.get("player")))
            ans = answers.pop(0) if answers else False
            e.answer([0] if ans else [1])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return logs


def _deck(e, p):
    return len(e.zlist("deck", p))


def test_decline_retriggers_and_use_consumes(rules):
    """使わないを選ぶと次の自分のターンにも再び聞かれ、使うと以後聞かれない。"""
    e = setup(rules, {"bz": ["T555"]}, {}, filler="T002")
    logs = _play(e, [False, False, False])
    # 自分のターンのはじめ（1,3,5）にだけ聞かれる。相手のターンには聞かれない
    assert logs == [(1, 0, 0), (3, 0, 0), (5, 0, 0)]
    deck_decline = _deck(e, 0)

    e = setup(rules, {"bz": ["T555"]}, {}, filler="T002")
    logs = _play(e, [True, True, True])
    assert logs == [(1, 0, 0)]   # 一度使うと以後トリガーしない
    # 宣言ドロー2枚ぶんだけ山札が多い減り方をしている
    assert deck_decline - _deck(e, 0) == 2
    # 印はプレイヤーごと: 自分は立ち、相手は立っていない
    assert e.eval_cond({"marked": {"name": "final_declaration", "scope": "game"}},
                       {"you": 0, "self": None, "vars": {}})
    assert not e.eval_cond({"marked": {"name": "final_declaration", "scope": "game"}},
                           {"you": 1, "self": None, "vars": {}})


def test_shared_gate_across_cards(rules):
    """2体の終極宣言がいても、使えるのはどちらか一度だけ（共有ゲート）。"""
    e = setup(rules, {"bz": ["T555", "T556"]}, {}, filler="T002")
    logs = _play(e, [False] * 6)
    deck_decline = _deck(e, 0)
    assert all(active == 0 for _, active, _ in logs)

    e = setup(rules, {"bz": ["T555", "T556"]}, {}, filler="T002")
    logs = _play(e, [True] * 6)
    # 全て「使う」と答えても、宣言ドローは一度きり（2枚ぶん）
    assert deck_decline - _deck(e, 0) == 2
    # 使った後は、どちらのカードも後続ターンで聞かれない
    assert all(turn == 1 for turn, _, _ in logs)


def test_each_player_once(rules):
    """お互いのプレイヤーが一度ずつ使える（印はプレイヤー独立）。
    P0 だけが使う運行と、両方が使う運行の比較で P1 の分を切り分ける。"""
    e = setup(rules, {"bz": ["T555"]}, {"bz": ["T555"]}, filler="T002")
    logs = _play(e, [True, True, True, True], turns=6)
    # P0 はターン1、P1 はターン2にそれぞれ一度だけ聞かれて使えた
    assert logs == [(1, 0, 0), (2, 1, 1)]
    deck_both = (_deck(e, 0), _deck(e, 1))
    for p in (0, 1):
        assert e.eval_cond({"marked": {"name": "final_declaration", "scope": "game"}},
                           {"you": p, "self": None, "vars": {}})

    e = setup(rules, {"bz": ["T555"]}, {"bz": ["T555"]}, filler="T002")
    logs = _play(e, [True, False, False, False, False], turns=6)
    # P0 は使い、P1 は断り続けるので自分のターンごとに聞かれ続ける
    assert logs[0] == (1, 0, 0)
    assert [lg for lg in logs if lg[2] == 1] == [(2, 1, 1), (4, 1, 1), (6, 1, 1)]
    # P0 の山札は両運行で同じ（流れが分岐していない対照）、P1 は宣言ドロー2枚ぶんだけ差
    assert _deck(e, 0) == deck_both[0]
    assert _deck(e, 1) - deck_both[1] == 2
