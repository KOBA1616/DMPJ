"""語彙パイロット第204弾: henrei（返霊）のイディオム確認。

返霊N はキーワード能力だが、本体は「攻撃誘発 → may［墓地からN枚を
好きな順序で山札の下へ → 支払えた場合だけ本体効果］」のイディオムで
書ける（キーワード自体はエンジンに無い。新規エンジン語彙なし）。

- 支払いの成否は move の as 束縛の枚数で判定する
  （{cmp: [{var: paid}, "==", N]}）。墓地がN枚未満なら支払えず、
  本体効果は発動しない
- 本体効果はカードごとに異なる（ドロー、全体破壊、蘇生、弱体化
  など既存語彙の組み合わせ）
- 地獄返霊（「その能力を使った時」も含む。dm36-005）は対象外として
  jigoku_henrei に分離する
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    parse_card(_proto_card("T511"), TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _attack_and_henrei(e, pay, limit=200):
    """T511 でプレイヤーを攻撃し、返霊の may に pay で答える。
    戻り値: (攻撃直前の手札, 収束後の (手札, 墓地, 山札)) 。"""
    hand0 = None
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if hand0 is None and d["kind"] == "attack" and d.get("player") == 0 \
                and "attack:T511:player" in keys:
            hand0 = len(e.zlist("hand", 0))
            e.answer([keys.index("attack:T511:player")])
            continue
        if hand0 is not None and d["kind"] == "charge":
            break
        if d["kind"] == "yes_no" and d.get("player") == 0 and "yes" in keys:
            e.answer([keys.index("yes" if pay else "no")])
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return hand0, (len(e.zlist("hand", 0)), len(e.zlist("graveyard", 0)),
                   len(e.zlist("deck", 0)))


def test_henrei_pay_draws(rules):
    """墓地2枚を山札の下へ戻して支払うと、本体（1ドロー）が発動する。"""
    e = setup(rules, {"bz": ["T511"], "graveyard": ["T002", "T002", "T002"]},
              {}, filler="T003")
    g0 = len(e.zlist("graveyard", 0))
    _, (hand, gy, deck) = _attack_and_henrei(e, pay=True)
    assert gy == g0 - 2
    # 手札: 攻撃前0 + ドロー1（相手ターン開始のドロー等は挟まらない範囲で測る）
    assert hand == 1


def test_henrei_decline(rules):
    """支払わなければ本体は発動せず、墓地も減らない（判別）。"""
    e = setup(rules, {"bz": ["T511"], "graveyard": ["T002", "T002", "T002"]},
              {}, filler="T003")
    g0 = len(e.zlist("graveyard", 0))
    _, (hand, gy, deck) = _attack_and_henrei(e, pay=False)
    assert gy == g0
    assert hand == 0
