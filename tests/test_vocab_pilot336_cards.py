"""語彙パイロット第336弾の対象カード（実カード parse）。

対象は pure な break_limit 3件で、ラウンド371で登録済み:
- dm29-001 光神龍ラル・アブゾーバー（partial はキーワードのみ。
  本弾で breaks_max の常在型を構成）
- dm16-008 インパクト・アブソーバー（partial の置換能力に
  未クロス時の常在型を足した）
- dm26rp1-039 我竜塔最高層 ローズ・キャッスル（partial の
  誘発2つにシールドゾーンの常在型を足した）

break_limit の行は残っていない（ファミリー解消）。

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


def test_targets_registered():
    rows = _rows()
    assert len(rows) == 2020
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10294
    assert not (ids & set(rows))          # canonical 重なり0
    for t, form, n in (("dm29-001", FORM_001, 1),
                       ("dm16-008", FORM_008, 2),
                       ("dm26rp1-039", FORM_039, 3)):
        c = _conv_cache.find(CONVERTED, t)
        assert c is not None and c["abilities"] == form, t
        assert not (c.get("source") or {}).get("unsupported")
        d = parse_card(c, TABLES)
        assert len(d.abilities) >= n
    left = {rid for rid, r in rows.items()
            if "break_limit" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


def test_proto_forms_match():
    assert proto_card("T1018")["abilities"] == FORM_001
    assert proto_card("T1019")["abilities"] == FORM_008
    assert proto_card("T1020")["abilities"] == FORM_039
