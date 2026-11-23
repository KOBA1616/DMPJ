"""語彙パイロット第344弾の対象カード（実カード parse）。

対象は pure な used_this_turn_condition 2件で、ラウンド379で登録:
- dmrp21-053 頂上演者 スケプティック（used_count の常在型）
- dm22rp1-002 ラクリマ・クロウラー（partial の二重の
  ジャストダイバー誘発は validate の dedupe で1つに畳まれて
  登録された。登録形は意図した形と完全一致）

used_this_turn_condition の pure 行は残っていない（残るのは
multi の dmrp14-s08 のみで、lose_prevention が別途必要）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
_conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from tests import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

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


def test_targets_registered():
    rows = _rows()
    assert len(rows) == 2001
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10312
    assert not (ids & set(rows))          # canonical 重なり0
    for tid, form in (("dmrp21-053", FORM_053),
                      ("dm22rp1-002", FORM_002)):
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None and c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    pure_left = {rid for rid, r in rows.items()
                 if r.get("gaps") == ["used_this_turn_condition"]}
    assert pure_left == set(), pure_left  # pure は解消（multi は残る）


def test_proto_forms_match():
    assert proto_card("T1037")["abilities"] == FORM_053
    assert proto_card("T1038")["abilities"] == FORM_002
