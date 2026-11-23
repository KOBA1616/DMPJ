"""語彙パイロット第348弾の対象カード（実カード parse）。

対象は pure な invasion_zero 3件すべてで、ラウンド383で登録:
- dmbd21-018 ZEROの侵略 ブラックアウト
- dmd35-011 ZEROの暴走 デッドリー・ハイウェイ
- promoy15-035 禁断の月 ドキンダムーン
（登録形は意図した形と完全一致）

invasion_zero は multi の dm24ex3-tf13 にだけ残る。

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

ZERO = {
    "kind": "trigger", "zone": "hand",
    "when": {"event": "turn_end"},
    "if": {"all": [{"is_turn": "opp"},
                   {"cmp": [{"turn_count": {"kind": "enter_unpaid",
                                            "owner": "opp",
                                            "filter": {"types": ["creature"]}}},
                            ">=", 1]}]},
    "effect": [{"op": "may",
                "body": [{"op": "move", "select": {"ref": "self"},
                          "to": "bz", "reason": "put"}]}],
}
ATK_018 = {
    "kind": "trigger",
    "when": {"event": "attack", "subject": "self"},
    "if": {"exists": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["d2_field"]}}},
    "effect": [{"op": "destroy",
                "select": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"]},
                           "extremal": "max_power", "count": 1}}],
}
DSW_011 = {
    "kind": "trigger", "dswitch": True,
    "when": {"event": "turn_start", "player": "you"},
    "effect": [{"op": "may",
                "body": [{"op": "dswitch"},
                         {"op": "destroy",
                          "select": {"zone": "bz", "owner": "opp",
                                     "filter": {"types": ["creature"],
                                                "tapped": True},
                                     "count": 1}}]}],
}
CIP_035 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "mill", "owner": "you", "count": 2}],
}
DSW_035 = {
    "kind": "trigger", "dswitch": True,
    "when": {"event": "turn_start", "player": "you"},
    "effect": [{"op": "may",
                "body": [{"op": "dswitch"},
                         {"op": "move",
                          "select": {"zone": "graveyard", "owner": "you",
                                     "filter": {"race_has": "ソニック・コマンド"},
                                     "count": 1},
                          "to": "bz", "reason": "put"}]}],
}

FORM_018 = [ZERO, ATK_018]
FORM_011 = [ZERO, DSW_011]
FORM_035 = [ZERO, CIP_035, DSW_035]


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_registered():
    rows = _rows()
    assert len(rows) == 1991
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10322
    assert not (ids & set(rows))          # canonical 重なり0
    for tid, form in (("dmbd21-018", FORM_018),
                      ("dmd35-011", FORM_011),
                      ("promoy15-035", FORM_035)):
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None and c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    left = {rid for rid, r in rows.items()
            if "invasion_zero" in (r.get("gaps") or [])}
    assert left == {"dm24ex3-tf13"}, left   # multi の1件だけ残る


def test_proto_forms_match():
    assert proto_card("T1046")["abilities"] == FORM_018
    assert proto_card("T1047")["abilities"] == FORM_011
    assert proto_card("T1048")["abilities"] == FORM_035
