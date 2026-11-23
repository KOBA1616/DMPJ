"""語彙パイロット第343弾: first_entry_tapped_per_turn（ドリフト）。

対象（pure 2件、同名カードの2刷）:
- dm26ex4-cho001 / dm26sd1-o002f アルカディアス・モモキング
  （各ターンはじめて出る相手のクリーチャーは、タップして出る）

形は第340弾（修羅丸「終斗」）で確立した first_time 誘発そのまま:
{kind: trigger, first_time: true, when: {event: move, to: bz,
subject: {owner: opp, filter: {types: [creature]}}},
effect: [tap {select: {ref: event.subject}}]}。
partial の2つの常在型（他のレクスターズ +2000、相手の
光でない呪文の禁止）はそのまま使う。

proto: T1036（モモキング型、カード全体）。

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

STATIC_POWER = {
    "kind": "static",
    "affects": {"zone": "bz", "owner": "you", "other": True,
                "filter": {"race_has": "レクスターズ"}},
    "mod": {"power": 2000},
}
STATIC_DENY = {
    "kind": "static",
    "affects": {"zone": "hand", "owner": "opp",
                "filter": {"types": ["spell"], "not_civs": ["light"]}},
    "mod": {"deny": ["cast"]},
}
FIRST_ENTRY = {
    "kind": "trigger", "first_time": True,
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp",
                         "filter": {"types": ["creature"]}}},
    "effect": [{"op": "tap", "select": {"ref": "event.subject"}}],
}

FORM = [STATIC_POWER, STATIC_DENY, FIRST_ENTRY]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    c = proto_card("T1036")
    assert c["abilities"] == FORM
    assert c["star"] is True
    parse_card(c, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz_card(e, p, defn):
    return next(c for c in e.bz_tops(p)
                if e.s.cards[c].defn == defn)


def _drive(e, plan, limit=900):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        if plan(d, _keys(d)):
            return d
    raise AssertionError("plan never stopped")


def test_t1036_only_first_entry_each_turn(rules):
    e = _build(rules, {"bz": ["T1036"]},
               {"hand": ["T005", "T009", "T004", "T003"],
                "mana": ["T005", "T009", "T004", "T001", "T001"]})
    state = {"p1turns": 0, "phase": 1, "played": set()}

    def plan(d, keys):
        if d["kind"] == "charge" and d.get("player") == 1:
            state["p1turns"] += 1
            if state["p1turns"] == 2 and "charge:T003" in keys:
                e.answer([keys.index("charge:T003")])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            return False
        if d["kind"] == "charge" and d.get("player") == 0:
            if state["phase"] == 1 and state["p1turns"] == 1 \
                    and {"T005", "T009"} <= state["played"]:
                return True
            if state["phase"] == 2 and state["p1turns"] == 2 \
                    and "T004" in state["played"]:
                return True
            if "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            return False
        if d["kind"] == "main" and d.get("player") == 1:
            for tgt in ("T005", "T009", "T004"):
                key = f"play:{tgt}"
                if key in keys and tgt not in state["played"]:
                    e.answer([keys.index(key)])
                    state["played"].add(tgt)
                    return False
        if d["kind"] == "pay_mana":
            keep = [i for i, k in enumerate(keys) if "T009" not in k]
            e.answer(keep[:d["min"]] if keep
                     else list(range(d["min"])))
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False

    _drive(e, plan)
    assert e.s.cards[_bz_card(e, 1, "T005")].tapped is True   # 1体目
    assert e.s.cards[_bz_card(e, 1, "T009")].tapped is False  # 2体目
    state["phase"] = 2
    _drive(e, plan)
    assert e.s.cards[_bz_card(e, 1, "T004")].tapped is True   # 次ターン1体目
