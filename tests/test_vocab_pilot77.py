"""語彙パイロット第77弾: attacked_trigger（攻撃された時）。

「このクリーチャーが攻撃された時」は attack イベント + target: self で表す。新語彙なし。
"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-at",
    "name": "試験被攻撃獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 4,
    "power": 5000,
    "races": ["テスト"],
    "text": "このクリーチャーが攻撃された時、カードを１枚引く。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "attack", "target": "self"},
         "effect": [
             {"op": "draw", "count": 1},
         ]},
    ],
    "source": {"official": "test-at", "review": "pending"},
}


def test_attacked_trigger_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"
    assert ab["when"]["target"] == "self"


def test_attacked_trigger_target_dict_parses():
    # 「相手が自分のクリーチャーを攻撃する時」形（target がセレクタ dict）
    card2 = dict(CARD)
    card2["abilities"] = [
        {"kind": "trigger",
         "when": {"event": "attack",
                  "target": {"owner": "you", "filter": {"types": ["creature"]}}},
         "effect": [{"op": "draw", "count": 1}]},
    ]
    parsed = parse_card(card2, TABLES)
    assert parsed is not None


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def keys(d):
    return [o["key"] for o in d["options"]]


def test_attacked_trigger_draws(rr):
    """タップした R077 が R070 に攻撃されると、R077 のコントローラーが1枚引く。"""
    e = setup(rr, {"bz": ["R070"]}, {"bz": ["R077"]})
    r077 = next(c for c in e.bz_tops(1) if e.s.cards[c].defn == "R077")
    e.s.cards[r077].tapped = True
    d = e.advance()
    while d["kind"] in ("charge", "main"):
        e.answer([keys(d).index("pass")])
        d = e.advance()
    assert d["kind"] == "attack"
    e.answer([keys(d).index("attack:R070:R077")])
    # 攻撃が解決し、相手ターン最初のチャージ判断まで進める
    for _ in range(30):
        d = e.advance()
        if d is None:
            break
        if d["player"] == 1 and d["kind"] == "charge":
            break
        ks = keys(d)
        if "no_block" in ks:
            e.answer([ks.index("no_block")])
        elif "pass" in ks:
            e.answer([ks.index("pass")])
        else:
            e.answer([0])
    # 手札 = ターン開始ドロー1 + 攻撃された時ドロー1 = 2（誘発がなければ1）
    hand1 = len([c for c in e.s.cards if c.zone == "hand" and c.owner == 1])
    assert hand1 == 2
    # バトル自体も行われ、4000 の R070 は 5000 の R077 に敗れて破壊されている
    assert e.bz_tops(0) == []
