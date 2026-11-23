"""再変換ラウンド380（第345弾 trigger_when_opponent_plays_free）の記録テスト。

- 新規登録3件: dm23rp3-025 運明！ベリアvs.キャディ /
  dm24bd5-008 魔力妖精バーベナ / dm24ex1-058 冥土人形
  ロッカ・マグナム（登録形は意図した形と完全一致）。
- converted 10,312→10,315 / rejects 2,001→1,998、
  canonical 重なり0・漏れ0。trigger_when_opponent_plays_free
  の行は残っていない（ファミリー解消）。

実挙動は登録カード自身で固定する（「支払わずに出る」側は
dm22rp1-002 ラクリマ・クロウラーで作る）。ドライバは
scenario.build の薄い包みで、tests.conftest は import しない
（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402

from tests import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

STATIC_025 = {"kind": "static", "affects": "self",
              "if": {"is_turn": "opp"}, "mod": {"power": 10000}}
TRIG_025 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp"}, "unpaid": True},
    "if": {"is_turn": "opp"},
    "effect": [{"op": "may",
                "body": [{"op": "move",
                          "select": {"zone": "deck", "owner": "you",
                                     "from_top": 1},
                          "to": "mana", "reason": "put"}]}],
}
TRIG_008 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp"}, "unpaid": True},
    "if": {"is_turn": "opp"},
    "effect": [{"op": "draw", "count": 1},
               {"op": "may",
                "body": [{"op": "choose",
                          "select": {"zone": "hand", "owner": "you",
                                     "filter": {"types": ["creature"],
                                                "cost_le": {"cost_of": "event.subject"}}},
                          "as": "put_card"},
                         {"op": "move", "select": {"ref": "put_card"},
                          "to": "bz", "reason": "put"}]}],
}
_EFF_058 = [{"op": "choose",
             "select": {"zone": "bz", "owner": "opp", "count": 1,
                        "chooser": "opp"},
             "as": "victim"},
            {"op": "destroy", "select": {"ref": "victim"}}]
TRIG_058A = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp"}, "unpaid": True},
    "if": {"is_turn": "opp"}, "effect": _EFF_058,
}
TRIG_058B = {
    "kind": "trigger",
    "when": {"event": "cast",
             "subject": {"owner": "opp",
                         "filter": {"types": ["spell"]}}},
    "if": {"is_turn": "opp"}, "effect": _EFF_058,
}
FORMS = {"dm23rp3-025": [STATIC_025, TRIG_025],
         "dm24bd5-008": [TRIG_008],
         "dm24ex1-058": [TRIG_058A, TRIG_058B]}
CRAWLER = "dm22rp1-002"


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round380_disposition():
    rej = _reject_rows()
    assert len(rej) == 1998
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10315
    assert not (ids & set(rej))          # canonical 重なり0
    for tid, form in FORMS.items():
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None and c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    left = {rid for rid, r in rej.items()
            if "trigger_when_opponent_plays_free" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _drive(e, plan, limit=900):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        if plan(d, _keys(d)):
            return d
    raise AssertionError("plan never stopped")


_P1 = {"hand": [CRAWLER, "T241"],
       "mana": ["T009", "T001", "T001", "T001", "T001"]}


def _crawler_plan(e, state, on_p1_choose=None):
    def plan(d, keys):
        if state.get("resolved") and d["kind"] == "charge" \
                and d.get("player") == 0:
            return True
        if d["kind"] == "main" and d.get("player") == 1 \
                and not state.get("cast") and "play:T241" in keys:
            e.answer([keys.index("play:T241")])
            state["cast"] = True
            return False
        if d["kind"] == "yes_no" and d.get("player") == 1:
            e.answer([keys.index("yes")])
            return False
        if d["kind"] == "yes_no" and d.get("player") == 0:
            state["p0_mays"] = state.get("p0_mays", 0) + 1
            state["resolved"] = True
            e.answer([keys.index("yes")])
            return False
        if d["kind"] == "choose_cards" and d.get("player") == 1 \
                and on_p1_choose:
            state["resolved"] = True
            on_p1_choose(e, d, keys)
            return False
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False
    return plan


def test_registered_beria_mana_boost(rules):
    e = _build(rules, {"bz": ["dm23rp3-025"], "mana": ["T001"]},
               dict(_P1))
    state = {}
    before = len(e.zlist("mana", 0))
    _drive(e, _crawler_plan(e, state))
    assert state.get("p0_mays", 0) >= 1
    assert len(e.zlist("mana", 0)) == before + 1


def test_registered_verbena_draw_and_put(rules):
    e = _build(rules, {"bz": ["dm24bd5-008"], "hand": ["T005"]},
               dict(_P1))
    state = {}
    _drive(e, _crawler_plan(e, state))
    assert state.get("p0_mays", 0) >= 1
    assert "T005" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert len(e.zlist("hand", 0)) == 2


def test_registered_rocca_two_triggers(rules):
    e = _build(rules, {"bz": ["dm24ex1-058"]},
               {**_P1, "bz": ["T004", "T005"]})
    state = {"picks": []}

    def pick(eng, d, keys):
        state["picks"].append(True)
        want = "T004" if len(state["picks"]) == 1 else "T005"
        idx = next(i for i, o in enumerate(d["options"])
                   if want in o["key"])
        eng.answer([idx])

    _drive(e, _crawler_plan(e, state, on_p1_choose=pick))
    assert len(state["picks"]) == 2
    gy = [e.s.cards[c].defn for c in e.zlist("graveyard", 1)]
    assert "T004" in gy and "T005" in gy
    assert CRAWLER in [e.s.cards[c].defn for c in e.bz_tops(1)]
