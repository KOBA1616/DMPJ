"""語彙パイロット第206弾: rainbonus（レインボーナス）のイディオム確認。

レインボーナスは条件付き能力の接頭辞で、本体は「バトルゾーンに自分の
多色クリーチャーがあれば」の条件 {exists: {zone: bz, owner: you,
filter: {types: [creature], multicolor: true}}} を trigger / replace /
static の if に置くイディオム。新規エンジン語彙なし。

ファミリーの形:
- 破壊置換: replace（instead: []）＋ if（第203弾と同じ形）
- 「攻撃できない能力を無視する」: キーワード cannot_attack_player を
  条件つき deny 静的（if: {not: 条件} の間だけ deny [attack_player]）
  に置き換えると観測可能な挙動が一致する
- 「次の相手のターンのはじめにアンタップしない」: tap op の
  no_untap_next フラグ。条件で切り替える場合は choose で束ねてから
  if/else で tap し分ける
- 「はじめて攻撃する時」: when の ord {kind: attack_by, eq: 1}（第159弾）
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T514", "T515")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _battle_sacrifice(e, limit=240):
    """まず相手の T397 に攻撃させてタップさせ（タップ状態でないと攻撃
    できない）、自分の T002 を攻撃させてバトルで失わせる。レイン
    ボーナスの may には「はい」と答える。攻撃直前の手札と収束後の手札。"""
    hand0 = None
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 1 \
                and "attack:T397:player" in keys:
            e.answer([keys.index("attack:T397:player")])
            continue
        if hand0 is None and d["kind"] == "attack" and d.get("player") == 0 \
                and any(k.startswith("attack:T002:T397") for k in keys):
            hand0 = len(e.zlist("hand", 0))
            e.answer([next(i for i, k in enumerate(keys)
                           if k.startswith("attack:T002:T397"))])
            continue
        if hand0 is not None and d["kind"] == "charge":
            return hand0, len(e.zlist("hand", 0))
        if d["kind"] == "yes_no" and "yes" in keys:
            e.answer([keys.index("yes")])
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return hand0, len(e.zlist("hand", 0))


def test_rainbonus_draws_with_multicolor(rules):
    """多色クリーチャーがいれば、破壊誘発で引ける。"""
    e = setup(rules, {"bz": ["T514", "T515", "T002"]}, {"bz": ["T397"]},
              filler="T003")
    hand0, hand1 = _battle_sacrifice(e)
    assert hand0 is not None and hand1 - hand0 == 1


def test_rainbonus_no_draw_without_multicolor(rules):
    """多色がいなければ引けない（判別）。"""
    e = setup(rules, {"bz": ["T514", "T001", "T002"]}, {"bz": ["T397"]},
              filler="T003")
    hand0, hand1 = _battle_sacrifice(e)
    assert hand0 is not None and hand1 - hand0 == 0
