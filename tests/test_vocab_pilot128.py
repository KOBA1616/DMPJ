"""語彙パイロット第128弾: facedown_mana（裏向きのままマナゾーンに置く）。

「裏向きのままマナゾーンに置く」は move op の face_down: true で表す（エンジン拡張:
move イベントが face_down を運び、_apply_one がマナゾーン到着時に裏向きにする。
move+flip_down の合成では置かれた瞬間が表向きになるため採用しない）。
裏向きのマナは無色・マナ数1として扱う（支払い側の既存処理）。
"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-fdm",
    "name": "試験裏向き呪文",
    "types": ["spell"],
    "civs": ["light"],
    "cost": 2,
    "text": "自分の山札の上から１枚目を、裏向きのままマナゾーンに置く。",
    "spell": [
        {"op": "move", "select": {"zone": "deck", "owner": "you", "from_top": 1},
         "to": "mana", "reason": "put", "face_down": True},
    ],
    "source": {"official": "test-fdm", "review": "pending"},
}


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def test_facedown_move_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    assert card.spell[0]["face_down"] is True


def test_facedown_mana_arrives_face_down(rr):
    """move イベント（face_down）でマナに置かれたカードは裏向きで、無色として扱われる。"""
    e = setup(rr, {}, {})
    top = e.s.zones["deck"][0][0]
    e._push(e.ev_task([{"ev": "move", "subject": e.s.ref(top), "to": "mana", "reason": "put", "face_down": True}]))
    d = e.advance()
    while d is not None:
        e.answer([0])
        d = e.advance()
    c = e.s.cards[top]
    assert c.zone == "mana" and c.face_down is True
    # 支払いでは無色として扱われる: 文明なし・コスト1の支払いには使えるが、火の文明は満たせない
    hand = next(i for i, x in enumerate(e.s.cards) if x.zone == "hand" and x.owner == 0)
    assert e._mana_choices(hand, 0, cost=1, civs=[]) != []
    assert e._mana_choices(hand, 0, cost=1, civs=["fire"]) == []


def test_face_up_mana_stays_face_up(rr):
    """対照: face_down を付けない移動では裏向きにならない。"""
    e = setup(rr, {}, {})
    top = e.s.zones["deck"][0][0]
    e._push(e.ev_task([{"ev": "move", "subject": e.s.ref(top), "to": "mana", "reason": "put"}]))
    d = e.advance()
    while d is not None:
        e.answer([0])
        d = e.advance()
    c = e.s.cards[top]
    assert c.zone == "mana" and c.face_down is False
