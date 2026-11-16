"""第3段・共通基盤その1: 相対ブレイク `mod: {breaks_add: N}`（breaks_add／breaks_increment の統一機構）。

- breaks の合成は能力ごとの最大値（max）で、「シールドをさらに1枚ブレイクする」
  （breaks_add／breaks_increment／breaks_plus_one）、「シールドを1つ少なくブレイクする」
  （breaks_reduction）、「次の攻撃だけ +1」（next_breaker）が書けなかった
  （design-full-bandA.md 単位6 型B、design-full-bandD.md 受け口 9-B）。
- 変更: MOD_KEYS に breaks_add を追加（defs.mod で int 検証、負値も可）。
  _chars_calc が mods の集約で合計し、集約の最後に break_opts の各値（ブレイカー能力が
  無い場合の既定1を含む）へ加算して breaks を最大値に更新する。509.2c の選択肢
  （combat が chars の break_opts から作る）も加算後の集合になる。0 未満にはならない。
  breaks_add が 0 のカードでは従来と完全一致する。
- breaks_reduction の2件（dmr21-007／dm23rp1-004）の文面は「相手のクリーチャーは
  すべて」という affects で対象を取る常在型なので、防御側の読み口を combat に別途
  足さなくても、この集約（発生源から見た owner: opp）でそのまま届く。
- proto: T232（W・ブレイカー＋自己加算）／T233（全体加算。dm23bd6-027 型）／
  T234（相手全体への減算。dmr21-007 型）／T235（modify で次の攻撃だけ、の形）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


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
    """T232〜T235 が parse でき、breaks_add の検証（int のみ、負値は可）が効く。"""
    for cid in ("T232", "T233", "T234", "T235"):
        parse_card(_proto_card(cid), TABLES)
    for bad_v in ("1", True, 1.5):
        bad = _proto_card("T232")
        bad["abilities"][0]["mod"] = {"breaks_add": bad_v}
        with pytest.raises(DefError):
            parse_card(bad, TABLES)


def test_no_change_without_breaks_add(rules):
    """後方互換: breaks_add が無いカードの break_opts／breaks は従来と完全一致する。"""
    e = setup(rules, {"bz": ["T001", "T017"]}, {})
    ch = e.chars(_cid(e, 0, "T001"))
    assert ch["breaks"] == 1 and ch["break_opts"] == [] and ch["breaks_add"] == 0
    ch = e.chars(_cid(e, 0, "T017"))
    assert ch["breaks"] == 2 and ch["break_opts"] == [2] and ch["breaks_add"] == 0


def test_self_add_on_double_breaker(rules):
    """W・ブレイカー持ちに breaks_add: 1 を与えるとブレイク数が3になる（設計 単位6 テスト3）。"""
    e = setup(rules, {"bz": ["T232"]}, {})
    ch = e.chars(_cid(e, 0, "T232"))
    assert ch["break_opts"] == [3] and ch["breaks"] == 3 and ch["breaks_add"] == 1


def test_global_add(rules):
    """全体加算: 通常のクリーチャーは既定1が2になり、W・ブレイカーは3になる。発生源自身にも届く。"""
    e = setup(rules, {"bz": ["T233", "T001", "T017"]}, {})
    assert e.chars(_cid(e, 0, "T001"))["break_opts"] == [2]
    assert e.chars(_cid(e, 0, "T017"))["break_opts"] == [3]
    assert e.chars(_cid(e, 0, "T233"))["break_opts"] == [2]


def test_reduction(rules):
    """減算: 相手の通常クリーチャーは0ブレイク（マイナスにならない）、W・ブレイカーは1になる。"""
    e = setup(rules, {"bz": ["T001", "T017"]}, {"bz": ["T234"]})
    ch = e.chars(_cid(e, 0, "T001"))
    assert ch["break_opts"] == [0] and ch["breaks"] == 0 and ch["breaks_add"] == -1
    ch = e.chars(_cid(e, 0, "T017"))
    assert ch["break_opts"] == [1] and ch["breaks"] == 1


def test_reduction_attack_breaks_nothing(rules):
    """実戦: 0ブレイクに減算された攻撃ではシールドは1枚も割れない。"""
    e = setup(rules, {"bz": ["T001"]}, {"bz": ["T234"]})
    _run_attack(e, "T001")
    assert len(e.zlist("shield", 1)) == 5
    assert len(e.zlist("hand", 1)) == 1   # ブレイク0枚＋相手ターン開始時のドロー1枚だけ


def test_add_attack_breaks_three(rules):
    """実戦: breaks_add を得た W・ブレイカーの攻撃はシールドを3枚ブレイクする。"""
    e = setup(rules, {"bz": ["T232"]}, {})
    _run_attack(e, "T232")
    assert len(e.zlist("shield", 1)) == 2
    assert len(e.zlist("hand", 1)) == 4   # ブレイクした3枚＋相手ターン開始時のドロー1枚


def test_modify_form(rules):
    """modify（duration つき）でも同じ mod が届く（next_breaker の形）。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T235"], "mana": ["T005"] * 2}, {})
    for _ in range(200):
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge":
            e.answer([keys.index("pass")])
        elif d["kind"] == "attack":
            break   # 解決が終わった（まだ自分のターンで、継続的効果も生きている）
        elif d["kind"] == "main":
            if "play:T235" in keys:
                e.answer([keys.index("play:T235")])
            else:
                break
        elif d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_cards":
            e.answer([keys.index("bz:T001:0")])
        else:
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    ch = e.chars(_cid(e, 0, "T001"))
    assert ch["break_opts"] == [2] and ch["breaks"] == 2 and ch["breaks_add"] == 1
