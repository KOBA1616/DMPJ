"""語彙パイロット第205弾: labyrinth（ラビリンス）のイディオム確認。

ラビリンスは条件名で、本体は「自分のシールド数 > 相手のシールド数」の
条件 {cmp: [{count: {zone: shield, owner: you}}, ">",
{count: {zone: shield, owner: opp}}]} を static / trigger の if に
置くイディオム。新規エンジン語彙なし。条件は能力の解決・特性計算の
たびに評価されるため、シールド数が変われば即座に追随する。

ファミリーの他条項で使う既存形: 攻撃先変更は起動型
{kind: activate, cost: {untap: self}, redirect: true}（第171弾）、
モード選択は {op: modal, modes: [...]}、バトル勝利誘発は
{event: battle_win, subject: self}、「そのターン攻撃が無かった」は
turn_count {kind: attack} の条件で読む。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T512", "T513")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def _cid(e, defn, player=0):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn)


def test_labyrinth_static_power(rules):
    """シールドが相手より多ければ +4000、同数なら基礎値のまま。"""
    e = setup(rules, {"bz": ["T512"]}, {"shield": ["T002", "T002", "T002"]},
              filler="T002")
    assert e.chars(_cid(e, "T512"))["power"] == 7000
    e2 = setup(rules, {"bz": ["T512"]}, {}, filler="T002")
    assert e2.chars(_cid(e2, "T512"))["power"] == 3000


def _summon_t513(e, limit=300):
    hand0 = None
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if hand0 is None and d["kind"] == "main" and d.get("player") == 0 \
                and any(k.startswith("play:T513") for k in keys):
            hand0 = len(e.zlist("hand", 0))
            e.answer([next(i for i, k in enumerate(keys)
                           if k.startswith("play:T513"))])
            continue
        if hand0 is not None:
            # 召喚直後の最初の決定の時点で CIP は解決済み（攻撃ステップは
            # 攻撃可能体がいなければ自動で飛ぶため、決定種別では測らない）
            return hand0, len(e.zlist("hand", 0))
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return hand0, len(e.zlist("hand", 0))


def test_labyrinth_cip_draws_when_ahead(rules):
    """シールドで勝っていれば CIP で引く（支払いで手札-1、ドロー+1）。"""
    e = setup(rules,
              {"hand": ["T513"], "mana": ["T030", "T030", "T030"]},
              {"shield": ["T002", "T002", "T002"]}, filler="T002")
    hand0, hand1 = _summon_t513(e)
    assert hand0 == 1 and hand1 == 1


def test_labyrinth_cip_no_draw_when_tied(rules):
    """同数では引かない（判別）。"""
    e = setup(rules, {"hand": ["T513"], "mana": ["T030", "T030", "T030"]},
              {}, filler="T002")
    hand0, hand1 = _summon_t513(e)
    assert hand0 == 1 and hand1 == 0
