"""語彙パイロット第352弾: optional_cost_reduction_per_count
（ドリフト）。

対象（pure 2件すべて）:
- dm31-033 爆獣パンダ・ブーリン（自分のマナゾーンの
  呪文1枚につき1軽減、下限1）
- dmbd16-007 聖霊龍騎セイント・ボルシャック（自分の墓地の
  エンジェル・コマンドまたはアーマード・ドラゴン1体につき
  1軽減、下限1）

形は第346弾（cost_may_per_count）で確立した
mod {cost: {amount: -1, count: <selector>}, cost_min: N}
そのもの。「少なくしてもよい」の任意性はコスト常在型の
自動適用の作法に倣う（第346弾と同方針）。数える対象が
2種族の和集合の場合は count セレクタの filter に any_of を
使うのが本弾の追加点。

proto: T1058（033型）/ T1059（007型）。

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

COST_033 = {"kind": "static", "zone": "hand", "affects": "self",
            "mod": {"cost": {"amount": -1,
                             "count": {"zone": "mana", "owner": "you",
                                       "filter": {"types": ["spell"]}}},
                    "cost_min": 1}}
COST_007 = {"kind": "static", "zone": "hand", "affects": "self",
            "mod": {"cost": {"amount": -1,
                             "count": {"zone": "graveyard", "owner": "you",
                                       "filter": {"any_of": [
                                           {"races": ["エンジェル・コマンド"]},
                                           {"races": ["アーマード・ドラゴン"]}]}}},
                    "cost_min": 1}}
POWER_WHEN_007 = {"kind": "static", "affects": "self",
                  "mod": {"power_when": {"amount": 4000,
                                         "when": "attacking"}}}

FORM_033 = [COST_033]
FORM_007 = [COST_007, POWER_WHEN_007]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    c = proto_card("T1058")
    assert c["abilities"] == FORM_033
    parse_card(c, TABLES)
    c = proto_card("T1059")
    assert c["abilities"] == FORM_007
    parse_card(c, TABLES)


def _build(rules, p0, p1=None):
    return scenario.build(rules, {"p0": p0, "p1": p1 or {},
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _play_options(e, target):
    """p0 の main 判断まで進め、target の play キーがあるか返す。
    main が出ないまま p0 の2回目の charge が来たら「出せない」
    として False（行動が無いターンは main 自体が省略される）。"""
    p0_charges = 0
    for _ in range(300):
        d = e.advance()
        if d is None:
            return False
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge" and d.get("player") == 0:
            p0_charges += 1
            if p0_charges >= 2:
                return False
        if d["kind"] == "main" and d.get("player") == 0:
            return f"play:{target}" in keys
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("main never reached")


def test_mana_spell_discount(rules):
    # マナに呪文3枚 → 9-3=6 で支払える（マナ6枚ちょうど）
    e = _build(rules, {"hand": ["T1058"],
                       "mana": ["T003", "T003", "T003",
                                "T001", "T001", "T001"]})
    assert _play_options(e, "T1058")
    # マナに呪文2枚 → 9-2=7 でマナ6枚では支払えない
    e = _build(rules, {"hand": ["T1058"],
                       "mana": ["T003", "T003",
                                "T001", "T001", "T001", "T001"]})
    assert not _play_options(e, "T1058")


def test_graveyard_race_discount(rules):
    # 墓地に対象種族2体 → 9-2=7 で支払える（マナ7枚ちょうど）
    e = _build(rules, {"hand": ["T1059"],
                       "mana": ["T004", "T004", "T004",
                                "T005", "T005", "T005", "T005"],
                       "graveyard": ["T156", "T156"]})
    assert _play_options(e, "T1059")
    # 墓地に対象種族1体 → 9-1=8 でマナ7枚では支払えない
    e = _build(rules, {"hand": ["T1059"],
                       "mana": ["T004", "T004", "T004",
                                "T005", "T005", "T005", "T005"],
                       "graveyard": ["T156"]})
    assert not _play_options(e, "T1059")
    # 墓地に対象外（T001）だけでは軽減されない
    e = _build(rules, {"hand": ["T1059"],
                       "mana": ["T004", "T004", "T004",
                                "T005", "T005", "T005", "T005"],
                       "graveyard": ["T001", "T001"]})
    assert not _play_options(e, "T1059")
