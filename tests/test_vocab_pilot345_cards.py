"""語彙パイロット第345弾の対象カード（実カード parse）。

対象は pure な trigger_when_opponent_plays_free 3件（未登録、
rejects 残存、いずれも partial は能力を持たない）:
- dm23rp3-025 運明！ベリアvs.キャディ
- dm24bd5-008 魔力妖精バーベナ
- dm24ex1-058 冥土人形ロッカ・マグナム

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
_conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import all_cards, proto_card  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402

TABLES = load_tables()
ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"

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

FORM_025 = [STATIC_025, TRIG_025]
FORM_008 = [TRIG_008]
FORM_058 = [TRIG_058A, TRIG_058B]
TARGETS = ("dm23rp3-025", "dm24bd5-008", "dm24ex1-058")


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _cand(tid, base):
    c = dict(base)
    c.pop("source", None)
    c.pop("gaps", None)
    return c


def test_targets_still_in_rejects():
    rows = _rows()
    conv_ids = {c["id"] for c in all_cards(CONVERTED)}
    for t in TARGETS:
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["trigger_when_opponent_plays_free"]


def test_partial_forms():
    rows = _rows()
    for tid, form in (("dm23rp3-025", FORM_025),
                      ("dm24bd5-008", FORM_008),
                      ("dm24ex1-058", FORM_058)):
        p = rows[tid]["partial"]
        assert not p.get("abilities")
        d = parse_card(_cand(tid, {**p, "abilities": form}), TABLES)
        assert len(d.abilities) >= 1


def test_proto_forms_match():
    assert proto_card("T1039")["abilities"] == FORM_025
    assert proto_card("T1040")["abilities"] == FORM_008
    assert proto_card("T1041")["abilities"] == FORM_058
