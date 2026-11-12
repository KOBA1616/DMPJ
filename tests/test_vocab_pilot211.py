"""語彙パイロット第211弾: battle_end_trigger（バトルの後）の確認。

バトルの終了時、両参加者を subject とする battle_end レコードが
出る（combat.py。バトルで場を離れた参加者の誘発は拾われないが、
「バトルの後、このクリーチャーを破壊する」は勝てば残っているし、
負ければ既に破壊されているので意味が一致する）。新規語彙なし:

- バトルの後、破壊する: trigger {when: {event: battle_end,
  subject: self}} → 破壊
- ブロックした時、バトルの後で: 相手のターン = 防御側、として
  if {is_turn: opp} で受ける
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T524", "T525")


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


def _drive(e, choices, limit=300):
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return
        keys = _keys(d)
        for pred, key in choices:
            if pred(d, keys):
                e.answer([keys.index(key)])
                break
        else:
            if d["kind"] == "pay_mana":
                e.answer(list(range(d["min"])))
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))


def _in(e, defn, zone, player=0):
    return any(e.s.cards[c].defn == defn and e.s.cards[c].controller == player
               for c in e.zlist(zone, player))


def test_destroy_after_won_battle(rules):
    """バトルに勝っても、バトルの後に破壊される。"""
    e = setup(rules, {"bz": ["T524"]}, {"bz": ["T002"]}, filler="T002")
    # 相手の T002 を攻撃できるよう、まず相手に T002 で殴らせず自分の
    # ターンに T524 で T002（タップ状態を作るため相手に攻撃させる）
    _drive(e, [
        (lambda d, k: d["kind"] == "attack" and d.get("player") == 1
         and "attack:T002:player" in k, "attack:T002:player"),
        (lambda d, k: d["kind"] == "block" and "no_block" in k, "no_block"),
        (lambda d, k: d["kind"] == "attack" and d.get("player") == 0
         and "attack:T524:T002" in k, "attack:T524:T002"),
    ])
    assert _in(e, "T524", "graveyard")
    assert not _in(e, "T524", "bz")


def test_no_battle_no_destroy(rules):
    """バトルしなければ破壊されない（判別）。"""
    e = setup(rules, {"bz": ["T524"]}, {"bz": ["T002"]}, filler="T002")
    _drive(e, [
        (lambda d, k: d["kind"] == "attack" and d.get("player") == 0
         and "attack:T524:player" in k, "attack:T524:player"),
        (lambda d, k: d["kind"] == "block" and "no_block" in k, "no_block"),
    ])
    assert _in(e, "T524", "bz")


def test_untap_after_block(rules):
    """ブロックして勝った後、アンタップする。"""
    e = setup(rules, {"bz": ["T525"]}, {"bz": ["T002"]}, filler="T002")
    attacked = blocked = False
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not attacked and d["kind"] == "attack" and d.get("player") == 1 \
                and "attack:T002:player" in keys:
            e.answer([keys.index("attack:T002:player")])
            attacked = True
            continue
        if attacked and not blocked and d["kind"] == "block" \
                and d.get("player") == 0:
            guard = [x for x in keys if x.startswith("bz:T525")]
            if guard:
                e.answer([keys.index(guard[0])])
                blocked = True
                continue
        if blocked and d["kind"] == "charge":
            break
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert attacked and blocked
    cids = [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T525"]
    assert cids and not e.s.cards[cids[0]].tapped
    assert _in(e, "T002", "graveyard", player=1)
