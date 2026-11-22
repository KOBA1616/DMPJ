"""語彙パイロット第336弾の対象カード（実カード parse）。

対象は pure な break_limit 3件（未登録、rejects 残存）:
- dm29-001 光神龍ラル・アブゾーバー（partial はキーワードのみ。
  本弾で breaks_max の常在型を構成）
- dm16-008 インパクト・アブソーバー（partial は置換能力を持ち、
  未クロス時の常在型だけが欠けていた）
- dm26rp1-039 我竜塔最高層 ローズ・キャッスル（partial は
  バトルの誘発2つを持ち、シールドゾーンの常在型だけが
  欠けていた）

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
_conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import all_cards, find  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()
ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"

FORM_001 = [{
    "kind": "static",
    "affects": {"owner": "opp", "filter": {"types": ["creature"]}},
    "mod": {"breaks_max": 1},
}]

FORM_008 = [
    {"kind": "replace",
     "when": {"event": "move", "from": "bz", "to": "graveyard",
              "reason": "destroy", "subject": "crossed"},
     "instead": [{"op": "move", "select": {"ref": "crossed"},
                  "to": "shield", "reason": "put"}]},
    {"kind": "static",
     "affects": {"owner": "any", "filter": {"types": ["creature"]}},
     "if": {"not": {"exists": {"ref": "self",
                               "filter": {"crossed": True}}}},
     "mod": {"breaks_max": 1}},
]

FORM_039 = [
    {"kind": "trigger", "zone": "shield", "if": {"face_up": True},
     "when": {"event": "battle_start",
              "subject": {"owner": "you",
                          "filter": {"types": ["creature"]}}},
     "effect": [{"op": "modify", "select": {"ref": "event.opponent"},
                 "mod": {"power": -4000}, "duration": "during_attack"}]},
    {"kind": "trigger", "zone": "shield", "if": {"face_up": True},
     "when": {"event": "battle_start",
              "opponent": {"owner": "you",
                           "filter": {"types": ["creature"]}}},
     "effect": [{"op": "modify", "select": {"ref": "event.subject"},
                 "mod": {"power": -4000}, "duration": "during_attack"}]},
    {"kind": "static", "zone": "shield", "if": {"face_up": True},
     "affects": {"owner": "opp", "filter": {"types": ["creature"]}},
     "mod": {"breaks_max": 1}},
]


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
    for t in ("dm29-001", "dm16-008", "dm26rp1-039"):
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["break_limit"]


def test_partial_forms():
    rows = _rows()
    p = rows["dm29-001"]["partial"]
    cand = _cand("dm29-001", {**p, "abilities": FORM_001})
    assert cand["keywords"] == ["blocker", "cannot_attack_player"]
    d = parse_card(cand, TABLES)
    assert len(d.abilities) >= 1
    p = rows["dm16-008"]["partial"]
    assert p["abilities"] == FORM_008[:1]        # 置換能力は既存
    cand = _cand("dm16-008", {**p, "abilities": FORM_008})
    d = parse_card(cand, TABLES)
    assert len(d.abilities) == 2
    p = rows["dm26rp1-039"]["partial"]
    assert p["abilities"] == FORM_039[:2]        # 誘発2つは既存
    cand = _cand("dm26rp1-039", {**p, "abilities": FORM_039})
    d = parse_card(cand, TABLES)
    assert len(d.abilities) >= 3


def test_proto_forms_match():
    assert proto_card("T1018")["abilities"] == FORM_001
    assert proto_card("T1019")["abilities"] == FORM_008
    assert proto_card("T1020")["abilities"] == FORM_039
