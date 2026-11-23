"""語彙パイロット第347弾: up_to_cost_reduction（ドリフト）。

対象（pure 3件のうち2件）:
- dmbd02-014 西南の超人（自分のジャイアントの召喚コストを
  最大2少なくしてもよい、ただし0以下にならない）
- dm39-018 大地幻獣ガガマル（マナゾーンにある自分の
  マナ爆誕クリーチャーを召喚するコストを最大2少なくして
  もよい、ただし1より少なくならない）

形: 「最大N少なく」は固定の mod {cost: -N} として扱う
（任意の軽減量の選択はコスト常在型では扱わない既存の作法）。
下限は cost_min（0 はエンジン既定なので省略、1 は明示）。
dm39-018 の対象は affects {zone: mana, filter: {keyword:
summon_from_mana}}。

dm23rp4x-tf03 は対象外: partial が完全に空（名前・原文・
能力なし）で、登録の基礎がない。

proto: T1044（014型、カード全体）/ T1045（018型）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
scenario.build を直接包む（第319弾以降の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

COST_014 = {
    "kind": "static",
    "affects": {"zone": "hand", "owner": "you",
                "filter": {"races": ["ジャイアント"]}},
    "mod": {"cost": -2},
}
SABER_014 = {
    "kind": "replace", "optional": True,
    "when": {"event": "move", "to": "graveyard", "reason": "destroy",
             "subject": {"owner": "you",
                         "filter": {"races": ["ジャイアント"]},
                         "other": True}},
    "instead": [{"op": "destroy", "select": {"ref": "self", "count": 1}}],
}
COST_018 = {
    "kind": "static",
    "affects": {"zone": "mana", "owner": "you",
                "filter": {"types": ["creature"],
                           "keyword": "summon_from_mana"}},
    "mod": {"cost": -2, "cost_min": 1},
}

FORM_014 = [COST_014, SABER_014]
FORM_018 = [COST_018]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    c = proto_card("T1044")
    assert c["abilities"] == FORM_014
    parse_card(c, TABLES)
    c = proto_card("T1045")
    assert c["abilities"] == FORM_018
    parse_card(c, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _drive_to_main(e, player=0, limit=300):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] == "main" and d.get("player") == player:
            return d, _keys(d)
        if "pass" in _keys(d):
            e.answer([_keys(d).index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("main never came")


def test_t1044_giant_discount(rules):
    # ジャイアント T356（コスト7）が 5 で召喚できる
    e = _build(rules, {"bz": ["T1044"], "hand": ["T356"],
                       "mana": ["T001"] * 5}, {})
    d, keys = _drive_to_main(e)
    assert "play:T356" in keys
    # マナ4では届かない
    e = _build(rules, {"bz": ["T1044"], "hand": ["T356"],
                       "mana": ["T001"] * 4}, {})
    d, keys = _drive_to_main(e)
    assert "play:T356" not in keys


def test_t1044_non_giant_not_discounted(rules):
    # ジャイアントでない T005（火・コスト3）はマナ2では出せない
    e = _build(rules, {"bz": ["T1044"], "hand": ["T005"],
                       "mana": ["T005", "T001"]}, {})
    d, keys = _drive_to_main(e)
    assert "play:T005" not in keys


def test_t1045_mana_summon_discount(rules):
    # マナ爆誕 T086（コスト2、通常召喚形）をマナから 1 で
    # 召喚できる（5→3 の確認は T730 の pay_cost でも別途見る）。
    # T730 は究極進化MAX で進化元が要るため召喚テストには使わない
    e = _build(rules, {"bz": ["T1045"],
                       "mana": ["T086", "T001"]}, {})
    d, keys = _drive_to_main(e)
    assert "play:T086:msum" in keys, keys
    e.answer([keys.index("play:T086:msum")])
    for _ in range(300):
        d = e.advance()
        assert d is not None
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] in ("charge", "attack"):
            break
        elif "pass" in _keys(d):
            e.answer([_keys(d).index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert "T086" in [e.s.cards[c].defn for c in e.bz_tops(0)]


def test_t1045_pay_cost_values(rules):
    # T730（コスト5）の pay_cost が発生源ありで 3、なしで 5
    e = _build(rules, {"bz": ["T1045"],
                       "mana": ["T730", "T001", "T001", "T001"]}, {})
    cid = next(c for c in e.zlist("mana", 0)
               if e.s.cards[c].defn == "T730")
    assert e.chars_ro(cid)["pay_cost"] == 3
    e = _build(rules, {"mana": ["T730", "T001", "T001", "T001"]}, {})
    cid = next(c for c in e.zlist("mana", 0)
               if e.s.cards[c].defn == "T730")
    assert e.chars_ro(cid)["pay_cost"] == 5


def test_t1045_no_discount_without_source(rules):
    # 発生源がいなければ T086 はコスト2のまま（支払いマナ1では不可）
    e = _build(rules, {"mana": ["T086", "T001"]}, {})
    d, keys = _drive_to_main(e)
    assert "play:T086:msum" not in keys
