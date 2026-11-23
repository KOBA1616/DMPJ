"""再変換ラウンド379（第344弾 used_this_turn_condition）の記録テスト。

- 新規登録2件: dmrp21-053 頂上演者 スケプティック /
  dm22rp1-002 ラクリマ・クロウラー（登録形は意図した形と
  完全一致。002 の partial の二重のジャストダイバー誘発は
  validate の dedupe で1つに畳まれた）。
- converted 10,310→10,312 / rejects 2,003→2,001、
  canonical 重なり0・漏れ0。used_this_turn_condition の
  pure 行は解消（multi の dmrp14-s08 は lose_prevention の
  ため残る）。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の作法）。
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

STATIC_053 = {
    "kind": "static", "affects": "self",
    "if": {"cmp": [{"used_count": {"owner": "you",
                                   "filter": {"types": ["spell",
                                                        "tamaseed"]}}},
                    "==", 0]},
    "mod": {"deny": ["attack_player", "attack_creature"]},
}
JUSTDIVER_002 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "modify", "select": {"ref": "self"},
                "mod": {"deny": ["be_chosen", "be_attacked"]},
                "duration": "until_next_own_turn_start"}],
}
CIVIL_002 = {
    "kind": "trigger",
    "when": {"event": "attack", "subject": "self"},
    "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                              "filter": {"civs": ["water"],
                                         "types": ["creature",
                                                   "tamaseed"]}}},
                    ">=", 3]},
    "effect": [{"op": "may", "body": [{"op": "draw", "count": 2}]}],
}
HAND_END_002 = {
    "kind": "trigger", "zone": "hand",
    "when": {"event": "turn_end"},
    "if": {"cmp": [{"used_count": {"owner": "you",
                                   "filter": {"types": ["spell",
                                                        "tamaseed"],
                                              "cost_ge": 5}}},
                    ">=", 1]},
    "effect": [{"op": "may",
                "body": [{"op": "move", "select": {"ref": "self"},
                          "to": "bz", "reason": "put"}]}],
}
FORM_053 = [STATIC_053]
FORM_002 = [JUSTDIVER_002, CIVIL_002, HAND_END_002]


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


def test_round379_disposition():
    rej = _reject_rows()
    assert len(rej) == 2001
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10312
    assert not (ids & set(rej))          # canonical 重なり0
    for tid, form in (("dmrp21-053", FORM_053),
                      ("dm22rp1-002", FORM_002)):
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None and c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    pure_left = {rid for rid, r in rej.items()
                 if r.get("gaps") == ["used_this_turn_condition"]}
    assert pure_left == set(), pure_left  # pure は解消


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


def test_registered_skeptic_attack_gate(rules):
    e = _build(rules, {"bz": ["dmrp21-053", "T005"], "hand": ["T003"],
                       "mana": ["T009", "T001"]},
               {})
    state = {"attacks_seen": 0, "cast": False, "snap": []}

    def plan(d, keys):
        if d["kind"] == "attack" and d.get("player") == 0:
            state["attacks_seen"] += 1
            state["snap"].append(list(keys))
            if state["attacks_seen"] == 2:
                return True
            e.answer([keys.index("pass")])
            return False
        if d["kind"] == "main" and d.get("player") == 0 \
                and state["attacks_seen"] == 1 \
                and not state["cast"] and "play:T003" in keys:
            e.answer([keys.index("play:T003")])
            state["cast"] = True
            return False
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False

    _drive(e, plan)
    first, second = state["snap"]
    assert "attack:T005:player" in first
    assert not any(k.startswith("attack:dmrp21-053") for k in first)
    assert "attack:dmrp21-053:player" in second


def test_registered_crawler_comes_out(rules):
    e = _build(rules, {"hand": ["dm22rp1-002", "T241"],
                       "mana": ["T009", "T001", "T001", "T001", "T001"]},
               {})
    state = {"cast": False, "may_seen": False}

    def plan(d, keys):
        if state["may_seen"] and d["kind"] == "charge" \
                and d.get("player") == 1:
            return True
        if d["kind"] == "main" and d.get("player") == 0 \
                and not state["cast"] and "play:T241" in keys:
            e.answer([keys.index("play:T241")])
            state["cast"] = True
            return False
        if d["kind"] == "yes_no" and d.get("player") == 0:
            state["may_seen"] = True
            e.answer([keys.index("yes")])
            return False
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False

    _drive(e, plan)
    assert state["may_seen"] is True
    assert "dm22rp1-002" in [e.s.cards[c].defn for c in e.bz_tops(0)]
