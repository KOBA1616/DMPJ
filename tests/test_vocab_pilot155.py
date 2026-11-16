"""語彙パイロット第155弾: link_establish_event（リンクした時）。

- G・リンクの手順（h_g_link）は状態変更のみで誘発収集用レコードを出さなかったため、
  「リンクした時」を受ける先が無かった（ラウンド182の実測）。本弾ではリンク手順の
  完了時点で、成立したグループの全員を subject とする合成レコード link_established を
  誘発収集に出す（第150弾 evolve_base と同型の追加。レコードは ev_task の束で出し、
  _apply_one は素通しする）。
- 誘発収集ではグループ全員が発生源になる（既存のリンク展開）ため、「リンクされる側
  （既に場にいたゴッド）」の「リンクした時」も誘発する。各メンバーの能力は、発生源が
  代表に正規化される既存の仕組みで、レコードのうち subject が代表のものに一致して
  1回だけ拾われる。
- 「カード3枚でリンクした時」のような枚数条件は、能力の if で既存の link_count 式
  （{link_count: self}）が判定する（収集時点でリンクは成立済み）。
- リンクを外しただけ・リンク先をパスした場合は成立ではないのでレコードは出ない。
- パターンA「出た時、またはリンクした時」（6件）は本弾の対象外: 出た時とリンクした時が
  別の誘発イベントであることは公式FAQ（2026-06-11変更）で裏取りできたが、一体の能力が
  リンクした状態で出た時に1回だけ誘発するのか2回誘発するのかは公式の裏取りが取れず、
  推測で回数を固めないため変換形を本弾では固定しない（docs/vocab-pilot.md 第155弾）。
- 誘発回数の数え方: 手札枚数はターン境界のドローでぶれるため、エンジンの trace
  （解決された誘発の因果記録）で link_established の解決回数をカード別に数える。
- proto は第154弾が T202 まで使ったため T203〜T205。
"""
from collections import Counter
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules, parse_card, load_tables

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def _setup(*args, **kwargs):
    e = setup(*args, **kwargs)
    e.s.trace = []      # 誘発の因果記録を有効にする（解決回数の実測用）
    return e


def _fires(e):
    """link_established で解決された誘発の回数（発生源の defn 別）。"""
    return Counter(t["src"] for t in e.s.trace if t["ev"] == "link_established")


def _play_god(e, defn, link_prefix=None, unlink_prefixes=()):
    """手札の defn を出し、リンク手順（外す→付ける）を指定どおりに進める。
    link_prefix が無ければリンク先はパスする。"""
    unlinks = list(unlink_prefixes)
    entered = False
    for _ in range(60):
        d = e.advance()
        if d is None:
            return
        if any(e.s.cards[c].defn == defn for c in e.zlist("bz", 0)):
            entered = True
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_unlink":
            hit = next((i for i, k in enumerate(keys)
                        if any(k.startswith(u) for u in unlinks)), None)
            if hit is not None:
                unlinks = [u for u in unlinks if not keys[hit].startswith(u)]
                e.answer([hit])
            else:
                e.answer([keys.index("done")])
            continue
        if d["kind"] == "choose_link_target":
            if link_prefix:
                e.answer([next(i for i, k in enumerate(keys) if k.startswith(link_prefix))])
            else:
                e.answer([keys.index("pass")])
            continue
        if entered:
            return   # リンク手順は出た直後に割り込む。それ以外の判断に移ったら手順は終わっている
        if d["kind"] == "main" and f"play:{defn}" in keys:
            e.answer([keys.index(f"play:{defn}")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def _flush(e, steps=60):
    """待機中の誘発が解決しきるまでだけ進める（ターンを進めない）。"""
    for _ in range(steps):
        if not e.s.pending:
            return
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))


def _god(e, defn):
    return next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == defn)


def test_proto_parse(rr):
    """T203〜T205 が parse でき、link_established の when が検証を通る。"""
    for cid in ("T203", "T204", "T205"):
        parse_card(_proto_card(cid), TABLES)
    for cid in ("T203", "T204", "T205"):
        card = next(c for c in rr.cards.values() if c.id == cid)
        trig = [a for a in card.face(None).abilities if a["kind"] == "trigger"]
        assert trig and trig[0]["when"] == {"event": "link_established", "subject": "self"}
    t204 = next(c for c in rr.cards.values() if c.id == "T204")
    assert t204.face(None).abilities[0]["if"] == {"cmp": [{"link_count": "self"}, ">=", 3]}


def test_no_link_no_fire(rules):
    """リンクしなければ「リンクした時」は誘発しない（単独で出る／リンク先をパス）。"""
    e = _setup(rules, {"hand": ["T203"], "mana": ["T008"] * 12}, {})
    _play_god(e, "T203")          # リンク先のゴッドがいない
    _flush(e)
    assert e.s.cards[_god(e, "T203")].link == 0
    assert _fires(e) == Counter()

    e = _setup(rules, {"bz": ["T203"], "hand": ["T205"], "mana": ["T008"] * 12}, {})
    _play_god(e, "T205")          # リンク先をパスする
    _flush(e)
    assert e.s.cards[_god(e, "T205")].link == 0 and e.s.cards[_god(e, "T203")].link == 0
    assert _fires(e) == Counter()


def test_both_sides_fire(rules):
    """判別: 出てリンクする側だけでなく、リンクされる側（既に場にいたゴッド）の
    「リンクした時」も誘発する。各1回ずつ。"""
    e = _setup(rules, {"bz": ["T203"], "hand": ["T205"], "mana": ["T008"] * 12}, {})
    _play_god(e, "T205", link_prefix="bz:T203")
    assert e.s.cards[_god(e, "T205")].link != 0
    assert e.s.cards[_god(e, "T205")].link == e.s.cards[_god(e, "T203")].link
    _flush(e)
    assert _fires(e) == Counter({"T203": 1, "T205": 1})


def test_link_count_condition(rules):
    """「カード3枚でリンクした時」（T204、黒幕型）は link_count の if で判定する:
    2枚リンクでは誘発せず、3枚目のリンク成立で誘発する。"""
    e = _setup(rules, {"bz": ["T203"], "hand": ["T204", "T205"], "mana": ["T008"] * 12}, {})
    _play_god(e, "T204", link_prefix="bz:T203")   # 中央が出て2枚リンク
    _flush(e)
    assert _fires(e) == Counter({"T203": 1})      # T204 は3枚条件を満たさない
    _play_god(e, "T205", link_prefix="bz:T204")   # 右が出て3枚リンク
    _flush(e)
    assert _fires(e) == Counter({"T203": 2, "T204": 1, "T205": 1})


def test_unlinked_member_does_not_fire(rules):
    """中央が出る際のリンク外しで外れたゴッドは、成立したグループに含まれないので
    その成立では「リンクした時」は誘発しない。グループに入った側だけが誘発する。"""
    e = _setup(rules, {"hand": ["T203", "T205", "T204"], "mana": ["T008"] * 12}, {})
    _play_god(e, "T203")
    _flush(e)
    _play_god(e, "T205", link_prefix="bz:T203")   # 2枚リンク: 両方1回ずつ
    _flush(e)
    assert _fires(e) == Counter({"T203": 1, "T205": 1})
    _play_god(e, "T204", link_prefix="bz:T203", unlink_prefixes=["bz:T205"])
    _flush(e)
    assert e.s.cards[_god(e, "T205")].link == 0                       # 外れた
    assert e.s.cards[_god(e, "T204")].link == e.s.cards[_god(e, "T203")].link != 0
    # T203 は新しい成立でもう1回。T205 はこの成立では誘発しない。T204 は2枚条件で不発。
    assert _fires(e) == Counter({"T203": 2, "T205": 1})


def test_unlink_only_no_establishment(rules):
    """リンクを外して付け直さなければ成立ではない: 誰の「リンクした時」も誘発しない。"""
    e = _setup(rules, {"hand": ["T203", "T205", "T204"], "mana": ["T008"] * 12}, {})
    _play_god(e, "T203")
    _flush(e)
    _play_god(e, "T205", link_prefix="bz:T203")
    _flush(e)
    assert _fires(e) == Counter({"T203": 1, "T205": 1})
    _play_god(e, "T204", unlink_prefixes=["bz:T205"])   # 外して、リンク先はパス
    _flush(e)
    assert e.s.cards[_god(e, "T204")].link == 0
    assert e.s.cards[_god(e, "T203")].link == 0       # 1枚だけ残ったので解消
    assert _fires(e) == Counter({"T203": 1, "T205": 1})   # 増えていない
