"""語彙パイロット第202弾: trigger_when_opponent_uses_s_trigger の確認。

「相手がS・トリガーを使った時」の誘発は既存だった: S・トリガーの宣言時に
合成レコード {ev: use_s_trigger, player: 使用者, subject: そのカード} が
誘発収集へ流れる（h_enqueue_st。第1412行付近）。したがって相手の使用は
{when: {event: use_s_trigger, player: opp}} で受ける。本弾はその挙動と、
ファミリーの他条項の形（2枚まで引く= repeat の may ドロー、山札から
S・トリガー呪文を探してシャッフルしてから唱える、等）を固定する。

なお「相手がS・トリガーを持つカードを使った時」（唱える/召喚するの両方）
は use_s_trigger ではなく、cast レコードと召喚 move への subject
フィルタ（keyword: s_trigger）で受けるのが正確（dmbd22-017）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    parse_card(_proto_card("T508"), TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _attack_and_break(e, limit=200):
    """T001 で攻撃してシールドを1枚割り、S・トリガーの宣言を受け入れ、
    誘発の解決まで進める。戻り値: 攻撃直前の自分の手札枚数と解決後の枚数。"""
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
        if d["kind"] == "declare_strigger" and keys:
            e.answer([0])   # S・トリガーを宣言する（空答えは宣言しないことになる）
            continue
        if d["kind"] == "yes_no" and "yes" in keys:
            e.answer([keys.index("yes")])
            continue
        if d["kind"] == "order_pending":
            st = next((i for i, k in enumerate(keys) if "strigger" in k), None)
            e.answer([st] if st is not None else list(range(d["min"])))
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return hand_at_attack, len(e.zlist("hand", 0))


def test_use_s_trigger_fires_draw(rules):
    """相手が割れたシールドの S・トリガー（T006）を使うと、T508 が誘発して引く。"""
    e = setup(rules, {"bz": ["T001", "T508"]}, {}, filler="T006")
    before, after = _attack_and_break(e)
    assert before is not None
    assert after - before == 1


def test_use_s_trigger_control(rules):
    """反応獣がいなければ引かない（判別）。"""
    e = setup(rules, {"bz": ["T001"]}, {}, filler="T006")
    before, after = _attack_and_break(e)
    assert before is not None
    assert after - before == 0
