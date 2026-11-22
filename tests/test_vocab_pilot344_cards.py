"""語彙パイロット第344弾の対象カード（実カード parse）。

対象は pure な used_this_turn_condition 2件（未登録、rejects 残存）:
- dmrp21-053 頂上演者 スケプティック（partial は能力を持たず、
  条項は used_count の常在型で足す）
- dm22rp1-002 ラクリマ・クロウラー（partial はジャストダイバー
  誘発が二重に入っている。登録時は1つに畳む。シビルカウント
  誘発は partial のまま）

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
    for t in ("dmrp21-053", "dm22rp1-002"):
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["used_this_turn_condition"]


def test_partial_forms():
    rows = _rows()
    p = rows["dmrp21-053"]["partial"]
    assert not p.get("abilities")
    d = parse_card(_cand("dmrp21-053", {**p, "abilities": FORM_053}),
                   TABLES)
    assert len(d.abilities) >= 1
    p = rows["dm22rp1-002"]["partial"]
    # partial はジャストダイバー誘発が二重（登録時は1つに畳む）
    assert p["abilities"] == [JUSTDIVER_002, JUSTDIVER_002, CIVIL_002]
    d = parse_card(_cand("dm22rp1-002", {**p, "abilities": FORM_002}),
                   TABLES)
    assert len(d.abilities) >= 3


def test_proto_forms_match():
    assert proto_card("T1037")["abilities"] == FORM_053
    assert proto_card("T1038")["abilities"] == FORM_002
