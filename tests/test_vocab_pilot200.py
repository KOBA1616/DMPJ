"""語彙パイロット第200弾: cast_resolution_destination（唱えた後の置き場所）。

「唱えた後、墓地に置くかわりに〜に置く」は既存の2形で表せることを固定する:

- 他のカードの効果で唱える場合: op play_free の resolve_to / resolve_position
  （ops.py の docstring に用例そのものがある）。行き先は hand / mana / deck
  （+ position: bottom）など。
- 呪文自身の恒常的な行き先: 面の resolve_to（チャージャー等が使う）。
  条件つきの自己帰還（「こうして火のカードを置いたら」）は、解決中の
  変数を置換の if で参照できないため対象外。
- ついでに判明した誤ラベル: 「自分の水のクリーチャーがN体以上あれば
  ゲームに勝つ」は cast と無関係で、{kind: state, if, effect: [{op: win}]}
  の常在勝利（SBA で評価）で表せる。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T503", "T504", "T505")


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


def _summon_and_resolve(e, defn, limit=240):
    """defn を召喚し、CIP の may を受け入れ、呪文の対象を取り、解決しきる。"""
    summoned = False
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not summoned and d["kind"] == "main" and d.get("player") == 0 \
                and f"play:{defn}" in keys:
            e.answer([keys.index(f"play:{defn}")])
            summoned = True
            continue
        if summoned and d["kind"] == "charge":
            break   # 次のターンに入った = 解決済み
        if d["kind"] == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys else list(range(d["min"])))
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def _zone_defns(e, zone, player=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, player)]


def test_play_free_resolve_to_hand(rules):
    """T503: 墓地の呪文を無料で唱えると、解決後は手札に戻る。"""
    e = setup(rules, {"hand": ["T503"], "mana": ["T030"] * 4,
                      "graveyard": ["T056"]},
              {"bz": ["T001"]}, filler="T002")
    _summon_and_resolve(e, "T503")
    assert "T056" in _zone_defns(e, "hand")
    assert "T056" not in _zone_defns(e, "graveyard")
    assert _zone_defns(e, "graveyard", 1) == ["T001"]   # 呪文自体は効いた


def test_play_free_resolve_to_deck_bottom(rules):
    """T504: 唱えた呪文は墓地ではなく山札の一番下へ。"""
    e = setup(rules, {"hand": ["T504"], "mana": ["T277"] * 4,
                      "graveyard": ["T056"]},
              {"bz": ["T001"]}, filler="T002")
    _summon_and_resolve(e, "T504")
    deck = _zone_defns(e, "deck")
    assert deck and deck[-1] == "T056"
    assert "T056" not in _zone_defns(e, "graveyard")


def test_state_win_condition(rules):
    """T505: 水のクリーチャーが3体そろうと勝つ。2体では勝たない（判別）。"""
    e = setup(rules, {"bz": ["T505", "T030", "T030"]}, {"bz": ["T001"]},
              filler="T002")
    for _ in range(60):
        d = e.advance()
        if d is None or e.s.result is not None:
            break
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert e.s.result is not None and e.s.result["winner"] == 0
    e = setup(rules, {"bz": ["T505", "T030"]}, {"bz": ["T001"]}, filler="T002")
    for _ in range(8):   # SBA は序盤に評価される。長く回すと山札切れで決着してしまう
        d = e.advance()
        if d is None or e.s.result is not None:
            break
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert e.s.result is None
