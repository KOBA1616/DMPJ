"""語彙パイロット第212弾: mana_number_change（マナの数字の変更）。

支払い（_mana_choices）でのマナの数字を変える3つの入口を新設した:

- 面フィールド mana_boost {filter?, value, optional?}: 出すカード自身の
  宣言。この支払いでのみ効く（「このクリーチャーを召喚する時、〜の
  マナの数字は1のかわりに2になる」必須形／「〜してもよい」任意形）
- 常在型の mana_boost {value | values, filter?, scope?, if?}: バトル
  ゾーンの発生源から、支払う側のすべての支払いに任意形で効く
  （「マナゾーンでカードをタップする時、好きな枚数のカードのマナを
  2にしてもよい」。scope: spell は呪文の支払いだけ）
- mod mana_number（int >= 2）: affects {zone: mana} の常在型が
  「マナの数字をNにする」を置換する。chars の mana_number で読む

あわせて式 distinct_type_count（対象群のカードタイプの種類数）を追加
（シビルカウント等の「カードタイプがNつ以上」の条件用）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T526", "T527", "T528", "T529", "T530", "T531", "T532", "T533",
       "T534", "T535")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def _cid_of(e, defn, zone, player=0):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn)


def _choices(e, defn):
    """手札の defn の支払い組み合わせ（_mana_choices の直接確認）。"""
    cid = _cid_of(e, defn, "hand")
    return e._mana_choices(cid, 0)


def test_face_boost_mandatory(rules):
    """ゴッド2枚が各2として数えられ、合計5に届く（T526 必須形）。"""
    e = setup(rules, {"hand": ["T526"], "mana": ["T531", "T531", "T002"]},
              {}, filler="T002")
    ch = _choices(e, "T526")
    assert ch and all(len(c) == 3 for c in ch)   # 2+2+1 の一意な組だけ
    # 対照: ブーストのない同コスト獣は 1+1+1=3 で届かない
    e = setup(rules, {"hand": ["T534"], "mana": ["T531", "T531", "T002"]},
              {}, filler="T002")
    assert _choices(e, "T534") == []
    # フィルタ外（ドラゴン）では効かない
    e = setup(rules, {"hand": ["T526"], "mana": ["T532", "T532", "T002"]},
              {}, filler="T002")
    assert _choices(e, "T526") == []


def test_face_boost_optional(rules):
    """任意形: ドラゴンを2として数える組が選べる（T527）。"""
    e = setup(rules, {"hand": ["T527"], "mana": ["T532", "T532", "T002"]},
              {}, filler="T002")
    assert _choices(e, "T527")   # 2+2+1
    # フィルタ外（ゴッド）では効かない
    e = setup(rules, {"hand": ["T527"], "mana": ["T531", "T531", "T002"]},
              {}, filler="T002")
    assert _choices(e, "T527") == []


def test_static_boost_any_payment(rules):
    """バトルゾーンの常在型ブーストは通常の支払いにも効く（T528）。"""
    e = setup(rules, {"hand": ["T534"], "bz": ["T528"],
                      "mana": ["T060", "T060", "T002"]}, {}, filler="T002")
    ch = _choices(e, "T534")
    assert ch and all(len(c) == 3 for c in ch)   # 2+2+1（3枚とも使う）
    # 対照: 発生源がいなければ 3 までしか届かない
    e = setup(rules, {"hand": ["T534"], "mana": ["T060", "T060", "T002"]},
              {}, filler="T002")
    assert _choices(e, "T534") == []
    # 相手のバトルゾーンにある発生源は効かない
    e = setup(rules, {"hand": ["T534"], "mana": ["T060", "T060", "T002"]},
              {"bz": ["T528"]}, filler="T002")
    assert _choices(e, "T534") == []


def test_static_boost_values(rules):
    """values [2, 3]: 2+3 で 5 に届く（T535）。"""
    e = setup(rules, {"hand": ["T534"], "bz": ["T535"],
                      "mana": ["T060", "T002"]}, {}, filler="T002")
    ch = _choices(e, "T534")
    assert ch and all(len(c) == 2 for c in ch)


def test_static_boost_spell_scope(rules):
    """scope: spell は呪文の支払いだけに効き、召喚には効かない（T529）。"""
    e = setup(rules, {"hand": ["T533"], "bz": ["T529"],
                      "mana": ["T060", "T060", "T002"]}, {}, filler="T002")
    assert _choices(e, "T533")   # 呪文は 2+2+1 で唱えられる
    e = setup(rules, {"hand": ["T534"], "bz": ["T529"],
                      "mana": ["T060", "T060", "T002"]}, {}, filler="T002")
    assert _choices(e, "T534") == []   # クリーチャーの召喚には効かない


def test_mana_number_mod_and_distinct_types(rules):
    """mod mana_number: マナのカードタイプ3種以上で全マナが2になる（T530）。"""
    # タイプ2種（クリーチャー＋呪文）では置換が働かず 1+1 で届かない
    e = setup(rules, {"hand": ["T530"], "bz": ["T530"],
                      "mana": ["T002", "T533"]}, {}, filler="T002")
    assert _choices(e, "T530") == []
    # タイプ3種（＋タマシード）で全マナが2になり 2+2 で届く
    e = setup(rules, {"hand": ["T530"], "bz": ["T530"],
                      "mana": ["T002", "T533", "T403"]}, {}, filler="T002")
    ch = _choices(e, "T530")
    assert ch and any(len(c) == 2 for c in ch)


def _keys(d):
    return [o["key"] for o in d["options"]]


def test_boosted_summon_enters(rules):
    """行動確認: ブーストで払った T526 がバトルゾーンに出て、マナ3枚がタップされる。"""
    e = setup(rules, {"hand": ["T526"], "mana": ["T531", "T531", "T002"]},
              {}, filler="T002")
    played = False
    for _ in range(200):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T526" in keys:
            e.answer([keys.index("play:T526")])
            played = True
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if played and any(e.s.cards[c].defn == "T526"
                          for c in e.zlist("bz", 0)):
            break
    assert played
    assert any(e.s.cards[c].defn == "T526" for c in e.zlist("bz", 0))
    tapped = [c for c in e.zlist("mana", 0) if e.s.cards[c].tapped]
    assert len(tapped) == 3


def test_mana_tap_trigger(rules):
    """subject の zone 指定（第212弾追加）: イベントとしてタップされた自分のマナは墓地に行く（T536）。

    支払いのマナタップは現状イベント化されていない（直接書き換え）ため、
    ここでは ev_task でタップイベントを直接流して照合だけを確認する。
    支払いタップのイベント化は mana_tap_trigger として別途残る。"""
    e = setup(rules, {"bz": ["T536"], "mana": ["T060", "T002"]},
              {}, filler="T002")
    cid = next(c for c in e.zlist("mana", 0) if e.s.cards[c].defn == "T060")
    e._push(e.ev_task([{"ev": "tap", "subject": e.s.ref(cid)}]))
    for _ in range(100):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert any(e.s.cards[c].defn == "T060" for c in e.zlist("graveyard", 0))
    assert len(e.zlist("mana", 0)) == 1   # タップされていない T002 は残る


def test_mana_tap_trigger_zone_control(rules):
    """バトルゾーンのクリーチャーがタップしても誘発しない（zone の判別）。"""
    e = setup(rules, {"bz": ["T536", "T002"], "mana": ["T060"]},
              {}, filler="T002")
    attacked = False
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not attacked and d["kind"] == "attack" and d.get("player") == 0 \
                and "attack:T002:player" in keys:
            e.answer([keys.index("attack:T002:player")])
            attacked = True
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        else:
            e.answer(list(range(d["min"])))
        if attacked and any(e.s.cards[c].defn == "T002" and e.s.cards[c].tapped
                            for c in e.zlist("bz", 0)):
            break
    assert attacked
    assert len(e.zlist("mana", 0)) == 1   # マナは墓地に行かない
    assert not any(e.s.cards[c].defn == "T060"
                   for c in e.zlist("graveyard", 0))
