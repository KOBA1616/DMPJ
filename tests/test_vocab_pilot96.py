"""語彙パイロット第96弾: opponent_chooses_branch（相手が選ぶ分岐）。

「相手は〜してもよい。そうしなければ…」は may の player: opp（本弾でエンジン拡張）と
may の else で表す。may の決定者は従来コントローラー固定だったため、ops.py の op_may に
player 引数を追加した（draw 等と同じ相対指定）。
"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def keys(d):
    return [o["key"] for o in d["options"]]


def to_attack(e):
    d = e.advance()
    while d["kind"] in ("charge", "main"):
        e.answer([keys(d).index("pass")])
        d = e.advance()
    assert d["kind"] == "attack", d["kind"]
    return d

CARD = {
    "id": "test-ocb",
    "name": "試験分岐獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 5,
    "power": 4000,
    "races": ["テスト"],
    "text": "このクリーチャーが出た時、相手は自身のクリーチャーを１体、手札に戻してもよい。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "summon", "subject": "self"},
         "effect": [
             {"op": "choose",
              "select": {"zone": "bz", "owner": "opp", "count": 1,
                         "filter": {"types": ["creature"]}},
              "as": "target"},
             {"op": "may", "player": "opp",
              "body": [
                  {"op": "move", "select": {"ref": "target"}, "to": "hand", "reason": "return"},
              ]},
         ]},
    ],
    "source": {"official": "test-ocb", "review": "pending"},
}


def test_opponent_may_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["effect"][1]["op"] == "may"


def test_opponent_may_player():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["effect"][1]["player"] == "opp"


def test_opponent_decides_may(rr):
    """R078 が攻撃する時、yes_no の決定は相手（player 1）に出され、相手が引ける。"""
    e = setup(rr, {"bz": ["R078"]}, {"bz": ["R077"]})
    e.s.cards[e.bz_tops(1)[0]].tapped = True
    before = len([c for c in e.s.cards if c.zone == "hand" and c.owner == 1])
    d = to_attack(e)
    atk = next(k for k in keys(d) if k.startswith("attack:R078"))
    e.answer([keys(d).index(atk)])
    d = e.advance()
    if d is not None and d["kind"] == "block":
        e.answer([keys(d).index("no_block")])
        d = e.advance()
    assert d["kind"] == "yes_no"
    assert d["player"] == 1              # 決定者は相手
    e.answer([0])                        # はい（引く）
    e.advance()
    after = len([c for c in e.s.cards if c.zone == "hand" and c.owner == 1])
    assert after == before + 1
