"""語彙パイロット第116弾: power_lt_card（そのカードよりパワーが小さい）— エンジン拡張。

新式 power_of（参照カードの現在パワー。cost_of の対）を追加した。
- defs: 式キーに power_of を追加
- selectors.eval_expr: power_of を評価（chars の現在パワー、複数なら最大）
- ついでに cost_of / power_of の参照解決を共通化（_expr_refs）:
  従来 {cost_of: {ref: t}} は実行時 TypeError、{cost_of: "self"} は 0 扱いだった
  潜在バグを、{ref:} 形式と "self" が正しく解決されるよう修正した。
「より小さい」は power_le: {sum: [{power_of: ...}, -1]} のイディオムで表す。
"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


CARD = {
    "id": "test-plc",
    "name": "試験弱者狩獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 5,
    "power": 5000,
    "races": ["テスト"],
    "text": "このクリーチャーが出た時、これよりパワーが小さい相手のクリーチャーを１体破壊する。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "move", "subject": "self", "to": "bz"},
         "effect": [
             {"op": "destroy",
              "select": {"zone": "bz", "owner": "opp",
                         "filter": {"power_le": {"sum": [{"power_of": {"ref": "self"}}, -1]}},
                         "count": 1}},
         ]},
    ],
    "source": {"official": "test-plc", "review": "pending"},
}


def test_power_lt_expr_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    f = card.abilities[0]["effect"][0]["select"]["filter"]
    assert f["power_le"] == {"sum": [{"power_of": {"ref": "self"}}, -1]}


def test_power_lt_trigger_shape():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["when"]["event"] == "move"
    assert ab["effect"][0]["select"]["owner"] == "opp"


def keys(d):
    return [o["key"] for o in d["options"]]


def to_attack(e):
    d = e.advance()
    while d["kind"] in ("charge", "main"):
        e.answer([keys(d).index("pass")])
        d = e.advance()
    assert d["kind"] == "attack", d["kind"]
    return d


def attack_and_resolve(e, atk_key):
    """攻撃を宣言し、攻撃誘発が解決し終わるまで汎用的に進める。
    対象が1体に定まる破壊は決定を経ずに自動解決される。"""
    d = to_attack(e)
    e.answer([keys(d).index(atk_key)])
    for _ in range(12):
        d = e.advance()
        if d is None:
            return
        if d["kind"] in ("attack", "charge", "main"):
            return
        if d["kind"] == "block":
            e.answer([keys(d).index("no_block")])
        elif d["kind"] == "choose_cards":
            e.answer([0])
        else:
            e.answer([0])


def test_power_of_behavior(rr):
    """R082（パワー5000）の攻撃時: パワー2000の T001 が破壊され、6000の R083 は残る。"""
    e = setup(rr, {"bz": ["R082"]}, {"bz": ["T001", "R083"]})
    t001 = next(c for c in e.bz_tops(1) if e.s.cards[c].defn == "T001")
    attack_and_resolve(e, "attack:R082:player")
    assert e.s.cards[t001].zone == "graveyard"
    assert {e.s.cards[c].defn for c in e.bz_tops(1)} == {"R083"}


def test_cost_of_dict_form_behavior(rr):
    """R081 の攻撃時: {cost_of: {ref: self}}（=5）で、コスト2の T001 が破壊され、コスト9の R083 は残る。"""
    e = setup(rr, {"bz": ["R081"]}, {"bz": ["T001", "R083"]})
    t001 = next(c for c in e.bz_tops(1) if e.s.cards[c].defn == "T001")
    attack_and_resolve(e, "attack:R081:player")
    assert e.s.cards[t001].zone == "graveyard"
    assert {e.s.cards[c].defn for c in e.bz_tops(1)} == {"R083"}
