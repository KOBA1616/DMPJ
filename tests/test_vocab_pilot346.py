"""語彙パイロット第346弾: cost_may_per_count（ドリフト）。

対象（pure 3件のうち2件）:
- dmc68-002 魔光帝フェルナンドVII世（自分の墓地の呪文1枚に
  つき召喚コスト-1、ただし1より少なくならない）
- dmx16-057 龍素記号Lp エクスペリオン（自分のリキッド・
  ピープル1体につき、自分の水の呪文のコスト-1、ただし1より
  少なくならない）

形は確立形: mod {cost: {amount: -1, count: <selector>},
cost_min: N}（dm21-020 / dm24ex1-016 等）。「少なくしてもよい」
の任意性はコスト常在型では自動適用として扱う既存の作法に倣う。

dmex17-031 は対象外: その原文には flagged gap の他に
デュアル・ザンジバルとナイト・マジックの条項があり、
コスト条項だけでは登録できない（rejects に残す）。

proto: T1042（002型、カード全体）/ T1043（057型）。

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

COST_002 = {
    "kind": "static", "zone": "hand", "affects": "self",
    "mod": {"cost": {"amount": -1,
                     "count": {"zone": "graveyard", "owner": "you",
                               "filter": {"types": ["spell"]}}},
            "cost_min": 1},
}
ATK_002 = {
    "kind": "trigger",
    "when": {"event": "attack", "subject": "self"},
    "effect": [{"op": "modify",
                "select": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"]},
                           "count": 1},
                "mod": {"power": {"amount": -1000,
                                  "count": {"zone": "graveyard",
                                            "owner": "you",
                                            "filter": {"types": ["spell"]}}}},
                "duration": "end_of_turn"}],
}
COST_057 = {
    "kind": "static",
    "affects": {"zone": "hand", "owner": "you",
                "filter": {"types": ["spell"], "civs": ["water"]}},
    "mod": {"cost": {"amount": -1,
                     "count": {"zone": "bz", "owner": "you",
                               "filter": {"race_has": "リキッド・ピープル"}}},
            "cost_min": 1},
}

FORM_002 = [COST_002, ATK_002]
FORM_057 = [COST_057]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    c = proto_card("T1042")
    assert c["abilities"] == FORM_002
    parse_card(c, TABLES)
    c = proto_card("T1043")
    assert c["abilities"] == FORM_057
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


def test_t1042_cost_reduced_by_graveyard_spells(rules):
    # 墓地の呪文3枚で 11-3=8。マナ8で召喚できる
    e = _build(rules, {"hand": ["T1042"],
                       "graveyard": ["T003", "T003", "T003"],
                       "mana": ["T053", "T001", "T001", "T001",
                                "T001", "T001", "T001", "T001"]},
               {})
    d, keys = _drive_to_main(e)
    assert "play:T1042" in keys
    e.answer([keys.index("play:T1042")])
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
    assert "T1042" in [e.s.cards[c].defn for c in e.bz_tops(0)]


def test_t1042_not_playable_one_mana_short(rules):
    # マナ7では 8 に届かず召喚できない
    e = _build(rules, {"hand": ["T1042"],
                       "graveyard": ["T003", "T003", "T003"],
                       "mana": ["T053", "T001", "T001", "T001",
                                "T001", "T001", "T001"]},
               {})
    d, keys = _drive_to_main(e)
    assert "play:T1042" not in keys


def test_t1042_cost_floor_one(rules):
    # 墓地の呪文12枚でもコストは1まで（cost_min: 1）
    e = _build(rules, {"hand": ["T1042"],
                       "graveyard": ["T003"] * 12,
                       "mana": ["T053"]},
               {})
    d, keys = _drive_to_main(e)
    assert "play:T1042" in keys


def test_t1043_water_spell_discount_per_liquid_people(rules):
    # リキッド・ピープル2体で水の呪文 T241（コスト5）が3になる
    e = _build(rules, {"bz": ["T1043", "T384", "T694"],
                       "hand": ["T241"],
                       "mana": ["T009", "T001", "T001"]},
               {})
    d, keys = _drive_to_main(e)
    assert "play:T241" in keys


def test_t1043_no_discount_without_liquid_people(rules):
    e = _build(rules, {"bz": ["T1043"], "hand": ["T241"],
                       "mana": ["T009", "T001", "T001"]},
               {})
    d, keys = _drive_to_main(e)
    assert "play:T241" not in keys
