"""語彙パイロット第209弾: alternative_summon_cost（代替コスト）の確認。

代替コストは面の alt_cost フィールド（既存）:
- {cost, civs, if?}: 別額のマナで支払う。[ff02] は {cost: 2,
  civs: [fire, fire]}。if は提示条件（マナゾーンの枚数など）
- {do: [{zone, filter?, count, to, reason}]}: 行動で支払う
  （自分のクリーチャーを4体破壊する等）

「そうしたら」の後続は、代替で支払った場合にだけ立つ条件
{alt_paid: true} を CIP 誘発の if に置いて書く（dm26ex2-075 の先例）。
ターン終わりの破壊＋ドローは delayed_trigger {when: turn_end}
（duration 省略 = end_of_turn）に載せる。
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
    parse_card(_proto_card("T520"), TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _play_keys(e, p=0):
    return [o["key"] for o in e._play_options(p)]


def _summon_and_finish_turn(e, key, limit=300):
    """指定キーで召喚し、相手のチャージまで進める。支払いが一意なら
    召喚は1回の advance で完了し、ターン終わりの遅延まで一気に進む
    ことがある。戻り値: (召喚直後の手札, 相手チャージ時点の手札)。"""
    played = False
    hand_after = None
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and key in keys:
            e.answer([keys.index(key)])
            played = True
            continue
        if played and hand_after is None:
            hand_after = len(e.zlist("hand", 0))
        if played and d["kind"] == "charge" and d.get("player") == 1:
            return hand_after, len(e.zlist("hand", 0))
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return hand_after, len(e.zlist("hand", 0))


def _in_zone(e, defn, zone):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, 0))


def test_alt_option_offered_and_followup(rules):
    """マナ3枚（火2含む）で代替が提示され、代替で召喚するとターン
    終わりに破壊され1枚引く。"""
    e = setup(rules, {"hand": ["T520"], "mana": ["T060", "T060", "T002"]},
              {}, filler="T002")
    assert "play:T520:alt" in _play_keys(e)
    # 支払いが一意なため召喚からターン終わりの破壊＋ドローまで
    # 暗黙に進む。最終状態で判定する（手札: 出した分 -1 ＋ドロー 1）
    _, hand_end = _summon_and_finish_turn(e, "play:T520:alt")
    assert _in_zone(e, "T520", "graveyard")
    assert hand_end == 1


def test_normal_payment_no_followup(rules):
    """通常コストで召喚すればターン終わりに破壊されない（判別）。"""
    e = setup(rules, {"hand": ["T520"],
                      "mana": ["T060", "T060", "T060", "T002", "T002", "T002"]},
              {}, filler="T002")
    hand_after, _ = _summon_and_finish_turn(e, "play:T520")
    assert hand_after == 0
    assert _in_zone(e, "T520", "bz")


def test_alt_not_offered_without_mana_count(rules):
    """マナが3枚未満では代替は提示されない（条件）。"""
    e = setup(rules, {"hand": ["T520"], "mana": ["T060", "T060"]},
              {}, filler="T002")
    assert "play:T520:alt" not in _play_keys(e)
