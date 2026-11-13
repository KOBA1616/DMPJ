"""語彙パイロット第203弾: unblocked_trigger（ブロックされなかった時）の確認。

「攻撃してブロックされなかった時」は、攻撃宣言の誘発から
{op: delayed_trigger, when: {event: break, player: <守る側>},
duration: during_attack} を仕掛ける形で表す（dm23-045 の登録先例）。
ブロックされればブレイクは起きず、遅延誘発は仕掛け直されない。
ブレイク・レコードの subject はブレイクしたクリーチャーなので、
「攻撃しているクリーチャーを破壊する」も {ref: event.subject} で書ける。

範囲: この形が拾えるのはプレイヤーへの攻撃（ブレイクを伴うもの）。
クリーチャーへの攻撃がブロックされなかった場合（バトルで決着）は
ブレイクが無いため拾えない（dmex10-041 は unblocked_creature_attack
として分離）。シールドが0枚の時の直接攻撃はゲーム終了で一致する。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T509", "T510")


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


def _attack_with_t001(e, block, limit=200):
    """T001 で攻撃する。block=True なら相手の T004 でブロックさせる。
    戻り値: 攻撃直前の自分の手札枚数と、収束後（次のチャージ時）の枚数。"""
    hand_at_attack = None
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if hand_at_attack is None and d["kind"] == "attack" \
                and d.get("player") == 0 and "attack:T001:player" in keys:
            hand_at_attack = len(e.zlist("hand", 0))
            e.answer([keys.index("attack:T001:player")])
            continue
        if hand_at_attack is not None and d["kind"] == "charge":
            return hand_at_attack, len(e.zlist("hand", 0))
        if d["kind"] == "block":
            guard = next((i for i, k in enumerate(keys) if k != "no_block"), None)
            if block and guard is not None:
                e.answer([guard])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "declare_strigger":
            e.answer(list(range(d["min"])))   # 宣言しない
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return hand_at_attack, len(e.zlist("hand", 0))


def test_unblocked_draws(rules):
    """ブロックされずにブレイクすると、遅延誘発で引く。"""
    e = setup(rules, {"bz": ["T001", "T509"]}, {}, filler="T002")
    before, after = _attack_with_t001(e, block=False)
    assert before is not None and after - before == 1


def test_blocked_no_draw(rules):
    """ブロックされるとブレイクが無く、引かない（判別）。"""
    e = setup(rules, {"bz": ["T001", "T509"]}, {"bz": ["T004"]}, filler="T002")
    before, after = _attack_with_t001(e, block=True)
    assert before is not None and after - before == 0


def test_end_turn_after_unblocked_attack(rules):
    """T510: 相手の攻撃がブロックされずブレイクすると、そのターンは
    終わる（相手の2体目の攻撃決定は出ない）。"""
    e = setup(rules, {"bz": ["T510"]}, {"bz": ["T001", "T001"]}, filler="T002")
    p1_attacks = 0
    saw_p0_charge = False
    for _ in range(200):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 1:
            p1_attacks += 1
            tgt = next((k for k in keys if k.endswith(":player")), None)
            e.answer([keys.index(tgt)] if tgt else list(range(d["min"])))
            continue
        if d["kind"] == "charge" and d.get("player") == 0 and p1_attacks >= 1:
            saw_p0_charge = True
            break
        if d["kind"] == "declare_strigger":
            e.answer(list(range(d["min"])))
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert p1_attacks == 1 and saw_p0_charge
