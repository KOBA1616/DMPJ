"""語彙パイロット第208弾: j_crime（Jクライム）のイディオム確認。

JクライムN は「攻撃する時、これと自分の墓地にあるコストN以下の
ジョーカーズ・クリーチャー1体を入れ替えてもよい」。入れ替えは既存の
op swap（701.26。入ったクリーチャーはタップ状態と攻撃中の状態を
引き継ぐ）で書ける。新規エンジン語彙なし:

  trigger {when: attack, subject: self} →
    may [ swap {out: {ref: self},
                in: {zone: graveyard, filter: {races: [ジョーカーズ],
                        cost_le: N}, count: 1},
                out_to: graveyard} ]
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T518", "T519")


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


def _attack_with_crime(e, swap, limit=240):
    """T518 で攻撃し、Jクライムの may に swap で答える。"""
    done = False
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not done and d["kind"] == "attack" and d.get("player") == 0 \
                and "attack:T518:player" in keys:
            e.answer([keys.index("attack:T518:player")])
            done = True
            continue
        if done and d["kind"] == "charge":
            break
        if d["kind"] == "yes_no" and d.get("player") == 0 and "yes" in keys:
            e.answer([keys.index("yes" if swap else "no")])
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return done


def _zone_defns(e, zone, player=0):
    return sorted(e.s.cards[c].defn for c in e.zlist(zone, player))


def test_jcrime_swaps(rules):
    """入れ替えると T518 は墓地へ、T519 が攻撃を引き継いで場に出る。"""
    e = setup(rules, {"bz": ["T518"], "graveyard": ["T519"]}, {}, filler="T002")
    assert _attack_with_crime(e, swap=True)
    assert _zone_defns(e, "graveyard") == ["T518"]
    assert "T519" in _zone_defns(e, "bz")


def test_jcrime_decline(rules):
    """入れ替えなければそのまま（判別）。"""
    e = setup(rules, {"bz": ["T518"], "graveyard": ["T519"]}, {}, filler="T002")
    assert _attack_with_crime(e, swap=False)
    assert _zone_defns(e, "graveyard") == ["T519"]
    assert "T518" in _zone_defns(e, "bz")
