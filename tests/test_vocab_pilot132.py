"""語彙パイロット第132弾: blocked_trigger（ブロックされた時）。

「このクリーチャーがブロックされた時」は when: {event: block, attacker: self} で表す。
新語彙なし。block レコードの subject はブロッカー側、attacker が攻撃クリーチャー。
"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules, load_tables, parse_card

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
    "id": "test-bt2",
    "name": "試験跳返獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 5,
    "power": 6000,
    "races": ["テスト"],
    "text": "このクリーチャーがブロックされた時、このクリーチャーをアンタップする。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "block", "attacker": "self"},
         "effect": [
             {"op": "untap", "select": {"ref": "self"}},
         ]},
    ],
    "source": {"official": "test-bt2", "review": "pending"},
}


def test_blocked_trigger_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "trigger"


def test_blocked_trigger_when():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["when"]["event"] == "block"
    assert ab["when"]["attacker"] == "self"


def test_blocked_trigger_untaps(rr):
    """R097 が R057（強制ブロック）にブロックされると、バトル後にアンタップしている。"""
    e = setup(rr, {"bz": ["R097"]}, {"bz": ["R057"]})
    d = to_attack(e)
    atk = next(k for k in keys(d) if k.startswith("attack:R097"))
    e.answer([keys(d).index(atk)])
    # R057 が自動でブロックしバトルが解決する。次の攻撃宣言機会では pass して攻撃を終える
    for _ in range(30):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main"):
            break
        ks = keys(d)
        if d["kind"] == "attack" and "pass" in ks:
            e.answer([ks.index("pass")])
        elif any(k.startswith("block") for k in ks):
            e.answer([next(i for i, k in enumerate(ks) if k.startswith("block"))])
        else:
            e.answer([0])
    mine = [c for c in e.bz_tops(0) if e.s.cards[c].defn == "R097"]
    assert len(mine) == 1
    assert e.s.cards[mine[0]].tapped is False   # ブロックされた時: アンタップした
    assert [c.defn for c in e.s.cards if c.zone == "graveyard" and c.defn == "R057"]
