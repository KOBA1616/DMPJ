"""語彙パイロット第210弾: number_choice（数字を1つ選ぶ）の確認。

数字選択の op choose_number は既存（宣言プリミティブ）: 選んだ整数は
GameState.declares に入り、式 {declared: 名前} で読める。新規エンジン
語彙なし。本弾はコスト連動の3効果を proto で固定する:

- 能力を無視する: modify {filter: {cost_le/ge: {declared: n}},
  mod: {ignore: [all]}, duration: until_next_own_turn_start}
- 唱えられない: 手札の呪文への modify {deny: [cast]}
- 攻撃もブロックもできない: modify {deny: [attack_player,
  attack_creature, block]}（action に単独の attack はない）

宣言の決定は kind "choose_one"、キーは "num:<n>"。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T521", "T522", "T523")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _cid(e, defn, player=None):
    for c in e.zlist("bz", 0) + e.zlist("hand", 0) + e.zlist("bz", 1) \
            + e.zlist("hand", 1):
        card = e.s.cards[c]
        if card.defn == defn and (player is None or card.controller == player):
            return c
    raise KeyError(defn)


def _cast_number_spell(e, num, limit=240):
    cast = chosen = False
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not cast and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T521" in keys:
            e.answer([keys.index("play:T521")])
            cast = True
            continue
        if cast and not chosen and f"num:{num}" in keys:
            e.answer([keys.index(f"num:{num}")])
            chosen = True
            continue
        if cast and chosen and d["kind"] in ("main", "attack", "charge"):
            return True
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return cast and chosen


def _setup(rules):
    return setup(rules,
                 {"hand": ["T521"], "mana": ["T030", "T030"]},
                 {"bz": ["T522", "T397"], "hand": ["T523"]},
                 filler="T002")


def test_number_effects(rules):
    """3を選ぶと: T522（コスト3）の能力が無視され（パワー基礎値）、
    攻撃できず、相手はコスト3の呪文を唱えられない。コスト7の T397 は
    影響を受けない。"""
    e = _setup(rules)
    assert _cast_number_spell(e, 3)
    t522 = _cid(e, "T522", player=1)
    t397 = _cid(e, "T397", player=1)
    t523 = _cid(e, "T523", player=1)
    assert e.chars(t522)["power"] == 3000
    assert e.permits(t522, "attack_player") is False
    assert e.permits(t523, "cast") is False
    assert e.permits(t397, "attack_player") is True


def test_number_control(rules):
    """4を選べばコスト3のカードは影響を受けない（判別）。"""
    e = _setup(rules)
    assert _cast_number_spell(e, 4)
    t522 = _cid(e, "T522", player=1)
    t523 = _cid(e, "T523", player=1)
    assert e.chars(t522)["power"] == 5000
    assert e.permits(t522, "attack_player") is True
    assert e.permits(t523, "cast") is True
