"""第3段・共通基盤その1: 条件アトム `{power_ge: N}`（power_threshold_breaker の前提）。

- 「自分のパワーがN以上なら T・ブレイカーを得る」型は、常在型の if に
  `{cmp: [{power_of: "self"}, ">=", N]}` と書くと chars の再入で無限再帰する
  （ラウンド187で実証。design-full-bandB.md §2-3 の精査観点）。
- 変更: cond アトム `{power_ge: N}` を追加（defs.cond で int 検証）。
  評価は Engine._threshold_power: 印刷パワー＋他の常在修整（他者の常在型・継続的効果・
  power_when を含む）。評価の連鎖が自分自身に戻ったら印刷パワーだけを返すため、
  条件を評価している常在型自身の修整は数に入らず、再帰せずに止まる。
- proto: T227（自分の +2000 で到達）／T228（未達）／T229（自己強化は自分の条件に
  数えない）／T230＋T231（他者の全体強化で到達）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import DefError, load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _cid(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _run_attack(e, att_defn):
    """P0 のターンで att_defn がプレイヤーを攻撃し、P0 のターンが終わるまで進める。"""
    for _ in range(300):
        d = e.advance()
        if d is None or (d["player"] == 1 and d["kind"] == "charge"):
            return
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack":
            e.answer([keys.index(f"attack:{att_defn}:player")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        else:
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("turn did not end")


def test_proto_parse(rules):
    """T227〜T231 が parse でき、power_ge の検証（int のみ）が効く。"""
    for cid in ("T227", "T228", "T229", "T230", "T231"):
        parse_card(_proto_card(cid), TABLES)
    for bad_v in ("6000", True, 6000.5):
        bad = _proto_card("T228")
        bad["abilities"][0]["if"] = {"power_ge": bad_v}
        with pytest.raises(DefError):
            parse_card(bad, TABLES)


def test_reached_by_own_boost(rules):
    """自分の常在修整（+2000）で閾値 6000 に届き、T・ブレイカー（breaks 3）を得る。再帰しない。"""
    e = setup(rules, {"bz": ["T227"]}, {})
    ch = e.chars(_cid(e, 0, "T227"))
    assert ch["power"] == 7000
    assert ch["breaks"] == 3 and ch["break_opts"] == [3]


def test_not_reached(rules):
    """修整が無ければ閾値に届かず、ブレイカーは得ない。"""
    e = setup(rules, {"bz": ["T228"]}, {})
    ch = e.chars(_cid(e, 0, "T228"))
    assert ch["power"] == 5000
    assert ch["breaks"] == 1 and ch["break_opts"] == []


def test_own_conditional_boost_not_counted(rules):
    """条件を評価している常在型自身の修整は閾値の数えに入らない（印刷＋他の常在修整）。
    自分自身の +2000 だけでは発火せず、パワーも上がらない。評価が止まること（無限再帰しない）も兼ねる。"""
    e = setup(rules, {"bz": ["T229"]}, {})
    ch = e.chars(_cid(e, 0, "T229"))
    assert ch["power"] == 5000
    assert ch["breaks"] == 1 and ch["break_opts"] == []


def test_reached_by_others_static(rules):
    """他者の全体強化（+3000）も「他の常在修整」に数え、閾値に届く。"""
    e = setup(rules, {"bz": ["T230", "T231"]}, {})
    ch = e.chars(_cid(e, 0, "T230"))
    assert ch["power"] == 7000
    assert ch["breaks"] == 2 and ch["break_opts"] == [2]


def test_threshold_breaker_breaks_three(rules):
    """実戦: 閾値到達した T227 の攻撃はシールドを3枚ブレイクする。"""
    e = setup(rules, {"bz": ["T227"]}, {})
    assert len(e.zlist("shield", 1)) == 5
    _run_attack(e, "T227")
    assert len(e.zlist("shield", 1)) == 2
    assert len(e.zlist("hand", 1)) == 4   # ブレイクした3枚＋相手ターン開始時のドロー1枚
