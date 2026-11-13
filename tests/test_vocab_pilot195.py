"""語彙パイロット第195弾: cross_free（コストを支払わずにクロスする）。

2系統ある。
- 許可（cross_free_permission）: 新アクション `cross_free`（permissions.yaml、
  default false）。メインステップの通常クロスで、ギア側の allow でも
  クリーチャー側の allow でも、other が相手側カードに当たれば無料の選択肢
  `cross:<ギア>:<クリーチャー>:free` が出る。支払う通常クロスも併記される。
- 効果（cross_free_op）: 新 op `cross_free {gear, to}`。gear セレクタで選んだ
  クロスギアすべてを、to セレクタで選んだクリーチャー1体に支払いなしで
  クロスする。crossed_to（第170弾）で「このクリーチャーにクロスしてあった
  ギア」を拾えるので、破壊時の再クロスも書ける。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T479", "T480", "T481", "T482", "T483")


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


def test_invalid_cross_free_op():
    base = {"id": "test-cf-bad", "name": "試験不良", "types": ["spell"],
            "civs": ["water"], "cost": 2, "mana": 1,
            "source": {"official": "test-cf-bad", "review": "pending"}}
    card = {**base, "spell": [{"op": "cross_free", "gear": {"zone": "bz"}}]}
    with pytest.raises(DefError):
        parse_card(card, TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _cid(e, defn, player=0):
    # バトルゾーンは共有ゾーンなので controller でも絞る
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _crossed_defns(e, defn, player=0):
    ref = e.s.ref(_cid(e, defn, player))
    return [e.s.cards[g].defn for g in e.crossed_gears(ref)]


def _drive(e, script, limit=160):
    """script: [(kind, key), ...]。該当する決定が出たらそのキーで答える。
    残りは pass / no_block / 最小限で流し、自分のメイン決定のキー一覧を集めて返す。"""
    script = list(script)
    mains = []
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0:
            mains.append(list(keys))
        hit = next((i for i, (k, key) in enumerate(script)
                    if k == d["kind"] and key in keys), None)
        if hit is not None:
            e.answer([keys.index(script.pop(hit)[1])])
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return mains


def test_creature_side_permission_no_mana(rules):
    """T479: マナが無くても、このクリーチャーへのクロスは無料で選べる。"""
    e = setup(rules, {"bz": ["T479", "T062"]}, {"bz": ["T001"]}, filler="T002")
    mains = _drive(e, [("main", "cross:T062:T479:free")])
    assert any("cross:T062:T479:free" in m for m in mains)
    assert not any("cross:T062:T479" in m for m in mains)   # 支払う方は出ない（判別）
    assert _crossed_defns(e, "T479") == ["T062"]


def test_no_permission_no_option(rules):
    """許可が無くマナも無ければ、クロスの選択肢自体が出ない（判別）。"""
    e = setup(rules, {"bz": ["T001", "T062"]}, {"bz": ["T001"]}, filler="T002")
    mains = _drive(e, [], limit=40)
    assert not any(k.startswith("cross:") for m in mains for k in m)
    assert e._cross_options(0) == []
    gear = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T062")
    assert e.s.cards[gear].crossed is None


def test_gear_side_permission_filter(rules):
    """T480: ギア側の許可。進化クリーチャーには無料、通常クリーチャーには出ない。"""
    e = setup(rules, {"bz": ["T480", "T017"]}, {"bz": ["T001"]}, filler="T002")
    mains = _drive(e, [("main", "cross:T480:T017:free")], limit=60)
    assert any("cross:T480:T017:free" in m for m in mains)
    assert _crossed_defns(e, "T017") == ["T480"]

    e = setup(rules, {"bz": ["T480", "T001"]}, {"bz": ["T001"]}, filler="T002")
    mains = _drive(e, [], limit=40)
    assert not any(k.startswith("cross:") for m in mains for k in m)


def test_paid_cross_still_works(rules):
    """通常の支払うクロスは従来どおり（回帰）。"""
    e = setup(rules, {"bz": ["T001", "T062"], "mana": ["T001", "T001"]},
              {"bz": ["T001"]}, filler="T002")
    # クロスが成立した直後に止めて、そのターンのうちに支払いを確認する
    for _ in range(60):
        d = e.advance()
        assert d is not None
        keys = _keys(d)
        if d["kind"] == "main" and "cross:T062:T001" in keys:
            e.answer([keys.index("cross:T062:T001")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if _crossed_defns(e, "T001") == ["T062"]:
            break
    assert _crossed_defns(e, "T001") == ["T062"]
    tapped = [e.s.cards[c].defn for c in e.zlist("mana", 0) if e.s.cards[c].tapped]
    assert tapped == ["T001", "T001"]


def test_op_via_activate(rules):
    """T481: 起動型能力（タップ）でギアを他のクリーチャーに無料クロスする。"""
    e = setup(rules, {"bz": ["T481", "T062", "T001"]}, {"bz": ["T001"]}, filler="T002")
    # 攻撃ステップの activate 選択肢を探して使う
    used = False
    for _ in range(200):
        d = e.advance()
        assert d is not None
        keys = _keys(d)
        act = next((k for k in keys if k.startswith("activate:") and "T481" in k), None)
        if act and not used:
            e.answer([keys.index(act)])
            used = True
            continue
        if d["kind"] == "choose_cards" and "bz:T001:0" in keys and used:
            e.answer([keys.index("bz:T001:0")])
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if used and _crossed_defns(e, "T001") == ["T062"]:
            break
    assert used
    assert _crossed_defns(e, "T001") == ["T062"]
    assert e.s.cards[_cid(e, "T481")].tapped


def test_op_via_cip(rules):
    """T482: 出た時、場のギアを自分に無料クロスする。"""
    e = setup(rules, {"hand": ["T482"], "mana": ["T269"] * 4, "bz": ["T062"]},
              {"bz": ["T001"]}, filler="T002")
    _drive(e, [("main", "play:T482"), ("yes_no", "yes")], limit=80)
    assert _crossed_defns(e, "T482") == ["T062"]


def test_destroyed_recross(rules):
    """T483: 破壊された時、クロスしてあったギアを他のクリーチャーに付け替える。"""
    e = setup(rules, {"bz": ["T483", "T001", "T062"],
                      "mana": ["T001", "T001"]},
              {"hand": ["T056"], "mana": ["T082", "T082", "T082"],
               "bz": ["T001"]}, filler="T002")
    _drive(e, [("main", "cross:T062:T483"), ("main", "play:T056"),
               ("choose_cards", "bz:T483:0"), ("yes_no", "yes")], limit=120)
    assert "T483" in [e.s.cards[c].defn for c in e.zlist("graveyard", 0)]
    assert _crossed_defns(e, "T001") == ["T062"]
