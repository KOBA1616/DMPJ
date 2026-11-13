"""語彙パイロット第207弾: deck_limit_exception の扱いの確認。

「4枚以上デッキに入れることができる」はデッキ構築のルールで、対戦中の
能力ではない。コーパスの変換済みカード（dmex13-057 等）でもこの文は
 defs に表されず、残りの条項だけで変換されている。本弾はその慣行と、
ファミリーの残り条項の形を固定する:

- 名前カウント条件の自己強化: {count: {filter: {name_has: …}}} の if
  ＋ mod {power, breaks}
- パワー閾値でのブレイカー獲得: if {power_ge: N}（自己参照は
  _threshold_power が再帰を避けて評価する）
- パワーアタッカーの体数比例: power_when {amount, count: <selector>,
  when: attacking}（selector の other: true で「自分の他の」）
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T516", "T517")


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


def _cids(e, defn):
    return [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == defn]


def test_name_count_clause(rules):
    """遊撃師団が5体いれば +5000 と W・ブレイカー、4体では基礎値。"""
    e = setup(rules, {"bz": ["T516"] * 5}, {}, filler="T002")
    ch = e.chars(_cids(e, "T516")[0])
    assert ch["power"] == 7000 and ch["breaks"] == 2
    e2 = setup(rules, {"bz": ["T516"] * 4}, {}, filler="T002")
    ch2 = e2.chars(_cids(e2, "T516")[0])
    assert ch2["power"] == 2000 and ch2["breaks"] == 1


def test_power_threshold_breaker(rules):
    """パワー6000以上で W・ブレイカーを得る（閾値条件）。"""
    e = setup(rules, {"bz": ["T517"]}, {}, filler="T002")
    ch = e.chars(_cids(e, "T517")[0])
    assert ch["power"] == 6000 and ch["breaks"] == 2
