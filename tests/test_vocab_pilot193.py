"""語彙パイロット第193弾: marshal_touch（マーシャル・タッチ）のイディオム。

「マーシャル・タッチ（このクリーチャーをバトルゾーンに出した時、自分の他の
クリーチャーを1体、バトルゾーンから手札に戻してもよい。そうした場合、この
クリーチャーの能力を使う）＋ 後続効果」は、新しいエンジン語彙なしで書ける:

    trigger（出た時）
      └ may
          ├ move（自分の他のクリーチャー1体 → 手札、reason: return、as: bounced）
          └ if {exists: {ref: bounced}} → 後続効果

- 戻さなければ（may を断る／他のクリーチャーがいない）後続効果は使えない。
- 後続効果が戻したクリーチャーを参照する形（コスト以下を破壊）は
  filter の cost_le: {cost_of: bounced} で書ける。
- ニンジャ・ストライク（第165弾）と同じく、キーワード能力そのものは
  エンジンに入れず、カード定義に展開形で持つ。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T473", "T474", "T475")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _defns(e, zone, player=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, player)]


def _bz(e, player):
    """バトルゾーンは共有ゾーンなので controller で絞る。"""
    return [e.s.cards[c].defn for c in e.zlist("bz", player)
            if e.s.cards[c].controller == player]


def _drive(e, plan, limit=300):
    """plan: {決定種別: [回答の列, ...]}。回答はキーの列か添字の列（第192弾と同じ）。"""
    plan = {k: list(v) for k, v in plan.items()}
    seen = {}
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return seen
        seen[d["kind"]] = seen.get(d["kind"], 0) + 1
        if d["kind"] in ("main", "attack", "charge") and not any(plan.values()):
            return seen
        keys = _keys(d)
        queue = plan.get(d["kind"])
        if queue:
            want = queue.pop(0)
            ans = [keys.index(w) if isinstance(w, str) else w for w in want]
            e.answer(sorted(set(ans)))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("drive did not finish")


def test_proto_parse():
    for cid in IDS:
        assert parse_card(_proto_card(cid), TABLES).types == ["creature"]


def test_return_then_destroy_blocker(rules):
    """T473: 自分の他クリーチャーを戻すと、相手のブロッカーを破壊できる。"""
    e = setup(rules, {"hand": ["T473"], "mana": ["T269"] * 4, "bz": ["T001"]},
              {"bz": ["T004", "T001"]}, filler="T002")
    _drive(e, {"main": [["play:T473"]], "yes_no": [["yes"]]})
    assert "T001" in _defns(e, "hand")            # 戻したクリーチャーは手札に
    assert _bz(e, 0) == ["T473"]                  # 自分自身は場に残る
    assert _bz(e, 1) == ["T001"]                  # ブロッカー T004 だけ破壊された
    assert _defns(e, "graveyard", 1) == ["T004"]


def test_decline_means_no_followup(rules):
    """T473: may を断ると何も戻らず、破壊も起きない（判別）。"""
    e = setup(rules, {"hand": ["T473"], "mana": ["T269"] * 4, "bz": ["T001"]},
              {"bz": ["T004"]}, filler="T002")
    _drive(e, {"main": [["play:T473"]], "yes_no": [["no"]]})
    assert _bz(e, 0) == ["T001", "T473"]
    assert _bz(e, 1) == ["T004"]
    assert _defns(e, "graveyard", 1) == []


def test_no_other_creature_means_no_followup(rules):
    """T473: 戻せる他のクリーチャーがいなければ、承諾しても破壊は起きない。"""
    e = setup(rules, {"hand": ["T473"], "mana": ["T269"] * 4},
              {"bz": ["T004"]}, filler="T002")
    _drive(e, {"main": [["play:T473"]], "yes_no": [["yes"]]})
    assert _bz(e, 0) == ["T473"]
    assert _bz(e, 1) == ["T004"]


def test_followup_cost_uses_returned_creature(rules):
    """T474: 戻したクリーチャー（コスト2）以下の相手だけが破壊対象になる。

    フィルタが効いていれば候補は相手の T001（コスト2）だけになり、選択は
    自動で確定する。コスト3の T004 は候補に入らず残る（判別）。
    """
    e = setup(rules, {"hand": ["T474"], "mana": ["T030"] * 5, "bz": ["T001"]},
              {"bz": ["T001", "T004"]}, filler="T002")
    _drive(e, {"main": [["play:T474"]], "yes_no": [["yes"]]})
    assert "T001" in _defns(e, "hand")
    assert _bz(e, 1) == ["T004"]                  # コスト3は残る
    assert _defns(e, "graveyard", 1) == ["T001"]


def test_followup_grants_speed_attacker(rules):
    """T475: 戻すとこのターン、このクリーチャーはスピードアタッカーを得て、
    出たターンに攻撃できる。"""
    e = setup(rules, {"hand": ["T475"], "mana": ["T001"] * 3, "bz": ["T001"]},
              {}, filler="T002")
    _drive(e, {"main": [["play:T475"]], "yes_no": [["yes"]]})
    assert "T001" in _defns(e, "hand")
    # 攻撃ステップで T475 が攻撃者として選べる（召喚酔いを SA が打ち消す）
    for _ in range(60):
        d = e.advance()
        assert d is not None
        if d["kind"] == "attack":
            keys = _keys(d)
            assert any(k.startswith("attack:") and "T475" in k for k in keys), keys
            return
        if "pass" in _keys(d):
            e.answer([_keys(d).index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("attack step never reached")
