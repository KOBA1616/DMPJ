"""語彙パイロット第219弾: draw_replacement_extra_card（引く時に余分に引く）。

2つの形がある:
  (a) ターンのはじめのドロー形: 「自分のターンのはじめにカードを1枚引くとき、
      もう1枚余分に引いてもよい」。ドローステップのドローそのものにだけ反応する
      必要があるため、基盤として st_draw が立てる turn_draw フラグを draw
      レコードに載せ、when の {turn_draw: true} で照合する（blocked 等と同型）。
  (b) そのターン1枚目のドロー形: 「自分のターンに1枚目のカードを引く時」。
      既存の when {ord: {kind: draw, eq: 1}} と cond {is_turn: you} の合成で
      表せる（追加ドローは ord 2 になるので再発しない）。

あわせて式 {max_power: selector}（対象群の最大パワー、無ければ0）を追加:
dm12-029 型の「自分の一番パワーの大きいクリーチャーが相手のどの
クリーチャーよりも大きければ」の条件用。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T563", "T564", "T565", "T566", "T567", "T568")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def _deck(e, p):
    return len(e.zlist("deck", p))


def _drive(e, handler, turns=5, limit=4000, stop_when=None):
    """handler(e, d) が True を返したらその判断は処理済み。それ以外は既定処理。
    stop_when(e, d) が真なら、その判断に答えずに止める（ターン境界の状態観測用）。"""
    for _ in range(limit):
        if e.s.turn > turns:
            break
        d = e.advance()
        if d is None:
            break
        if stop_when is not None and stop_when(e, d):
            break
        if handler(e, d):
            continue
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def test_turn_draw_may(rules):
    """(a) ターン頭ドロー形: 自分のドローがあるターン（3,5）だけ聞かれ、
    受けると1枚余分に引く。"""
    logs = []

    def make_handler(accept):
        def h(e, d):
            if d["kind"] == "yes_no":
                logs.append((e.s.turn, d.get("player")))
                e.answer([0] if accept else [1])
                return True
            return False
        return h

    e = setup(rules, {"bz": ["T563"]}, {}, filler="T002")
    _drive(e, make_handler(False))
    assert logs == [(3, 0), (5, 0)]
    deck_decline = _deck(e, 0)

    logs.clear()
    e = setup(rules, {"bz": ["T563"]}, {}, filler="T002")
    _drive(e, make_handler(True))
    assert logs == [(3, 0), (5, 0)]
    assert deck_decline - _deck(e, 0) == 2   # 2ターン × 余分1枚


def test_effect_draw_is_not_turn_draw(rules):
    """(a) 効果ドローでは反応しない: 呪文で2枚引いても may は聞かれない。"""
    logs = []
    cast = []

    def h(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "yes_no":
            logs.append((e.s.turn, d.get("player")))
            e.answer([1])   # ターン頭分は断る
            return True
        if d["kind"] == "main" and "play:T567" in keys and not cast:
            cast.append(e.s.turn)
            e.answer([keys.index("play:T567")])
            return True
        return False

    e = setup(rules, {"bz": ["T563"], "hand": ["T567"], "mana": ["T030", "T030"]}, {},
              filler="T002")
    start = _deck(e, 0)
    _drive(e, h, turns=3)
    assert cast, "呪文を唱えられていない"
    assert logs == [(3, 0)]            # 聞かれたのはターン頭ドローの分だけ
    assert start - _deck(e, 0) == 3    # ターン頭1枚 + 呪文2枚（余分は引いていない）


def test_first_draw_fires_on_effect_draw(rules):
    """(b) 1枚目形: 先攻1ターン目はターンドローが無いので、呪文の最初の
    ドローが「1枚目」になり反応する。2枚目では反応しない。"""
    logs = []

    def h(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "yes_no":
            logs.append((e.s.turn, d.get("player")))
            e.answer([0])
            return True
        if d["kind"] == "main" and "play:T567" in keys:
            e.answer([keys.index("play:T567")])
            return True
        return False

    e = setup(rules, {"bz": ["T564"], "hand": ["T567"], "mana": ["T030", "T030"]}, {},
              filler="T002")
    start = _deck(e, 0)
    _drive(e, h, turns=1)
    assert logs == [(1, 0)]            # 呪文の1枚目で一度だけ
    assert start - _deck(e, 0) == 3    # 呪文2枚 + 余分1枚


def test_first_draw_on_turn_draw(rules):
    """(b) 通常ケース: 自分のターンのドローが1枚目として反応する。"""
    logs = []

    def h(e, d):
        if d["kind"] == "yes_no":
            logs.append((e.s.turn, d.get("player")))
            e.answer([0])
            return True
        return False

    e = setup(rules, {"bz": ["T564"]}, {}, filler="T002")
    start = _deck(e, 0)
    _drive(e, h, turns=3)
    assert logs == [(3, 0)]
    assert start - _deck(e, 0) == 2    # ターンドロー1枚 + 余分1枚


def test_first_draw_not_on_opponent_turn(rules):
    """(b) 相手のターンに引いても反応しない（is_turn の門）:
    各プレイヤーが引く呪文を自分が唱え、相手のドローでは相手の初ドロー獣は
    反応せず、自分の分だけ反応する。"""
    logs = []
    deck1_at_p1_may = []

    def h(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "yes_no":
            logs.append((e.s.turn, d.get("player")))
            if d.get("player") == 1:
                deck1_at_p1_may.append(_deck(e, 1))
            e.answer([0])
            return True
        if d["kind"] == "main" and "play:T568" in keys:
            e.answer([keys.index("play:T568")])
            return True
        return False

    e = setup(rules, {"bz": ["T564"], "hand": ["T568"], "mana": ["T030", "T030"]},
              {"bz": ["T564"]}, filler="T002")
    start1 = _deck(e, 1)
    _drive(e, h, turns=2)
    # ターン1（自分のターン）で聞かれたのは自分だけ。相手はターン1には聞かれない
    assert [lg for lg in logs if lg[0] == 1] == [(1, 0)]
    # 相手が自分のターン（ターン2）のドローで聞かれた時点では、相手の山札は
    # 呪文の1枚＋ターンドロー1枚だけ減っている（ターン1の余分ドローは無い）
    assert deck1_at_p1_may and start1 - deck1_at_p1_may[0] == 2


def test_conditional_max_power(rules):
    """(a) 条件形: 自分の一番大きいクリーチャーが相手の全員より大きければ
    反応する。相手が大きければ反応しない。"""
    logs = []

    def h(e, d):
        if d["kind"] == "yes_no":
            logs.append((e.s.turn, d.get("player")))
            e.answer([1])
            return True
        return False

    e = setup(rules, {"bz": ["T565"]}, {"bz": ["T002"]}, filler="T002")   # 4000 > 1000
    _drive(e, h, turns=3)
    assert logs == [(3, 0)]

    logs.clear()
    e = setup(rules, {"bz": ["T565"]}, {"bz": ["T201"]}, filler="T002")   # 4000 < 9000
    _drive(e, h, turns=3)
    assert logs == []

    logs.clear()
    e = setup(rules, {"bz": ["T565", "T201"]}, {"bz": ["T002"]}, filler="T002")
    _drive(e, h, turns=3)
    assert logs == [(3, 0)]   # 自分の別クリーチャー（9000）が一番でもよい


def test_up_to_two_and_turn_end_tap(rules):
    """dm14-017 形: ターン頭に0〜2枚余分に引き、自分のターンの終わりに
    自分のクリーチャーを2体タップする。"""
    def make_handler(num):
        def h(e, d):
            keys = [o["key"] for o in d["options"]]
            if d["kind"] == "choose_one" and keys and keys[0].startswith("num:"):
                e.answer([num])
                return True
            return False
        return h

    # ターン4（相手ターン）の最初の判断で止める: ターン3終わりのタップが
    # 適用済みで、ターン5開始のアンタップ前
    stop4 = lambda e, d: e.s.turn >= 4

    e = setup(rules, {"bz": ["T566", "T002", "T002"]}, {}, filler="T002")
    start = _deck(e, 0)
    _drive(e, make_handler(2), turns=5, stop_when=stop4)
    assert start - _deck(e, 0) == 3    # ターンドロー1枚 + 余分2枚
    mine = [c for c in e.zlist("bz", 0) if e.s.cards[c].controller == 0]
    assert len(mine) == 3
    assert sum(1 for c in mine if e.s.cards[c].tapped) == 2   # 終わりに2体タップ

    e = setup(rules, {"bz": ["T566", "T002", "T002"]}, {}, filler="T002")
    start = _deck(e, 0)
    _drive(e, make_handler(0), turns=5, stop_when=stop4)
    assert start - _deck(e, 0) == 1    # 余分0枚でもタップの支払いは残る
    mine = [c for c in e.zlist("bz", 0) if e.s.cards[c].controller == 0]
    assert sum(1 for c in mine if e.s.cards[c].tapped) == 2


def test_turn_end_tap_degrades_with_few_creatures(rules):
    """タップできるクリーチャーが1体しかいなければ、その1体をタップして済む。"""
    e = setup(rules, {"bz": ["T566"]}, {}, filler="T002")
    _drive(e, lambda e, d: False, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    mine = [c for c in e.zlist("bz", 0) if e.s.cards[c].controller == 0]
    assert len(mine) == 1 and e.s.cards[mine[0]].tapped
