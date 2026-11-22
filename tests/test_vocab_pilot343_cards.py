"""語彙パイロット第343弾の対象カード（実カード parse）。

対象は pure な first_entry_tapped_per_turn 2件（未登録、
rejects 残存、同名カードの2刷）:
- dm26ex4-cho001 / dm26sd1-o002f アルカディアス・モモキング
  （partial は2つの常在型を持ち、出る時の条項だけが欠けていた）

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
    for t in ("dm26ex4-cho001", "dm26sd1-o002f"):
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["first_entry_tapped_per_turn"]


def test_partial_forms():
    rows = _rows()
    for t in ("dm26ex4-cho001", "dm26sd1-o002f"):
        p = rows[t]["partial"]
        assert p["abilities"] == [STATIC_POWER, STATIC_DENY]
        cand = _cand(t, {**p, "abilities": FORM})
        d = parse_card(cand, TABLES)
        assert len(d.abilities) >= 3


def test_proto_forms_match():
    assert proto_card("T1036")["abilities"] == FORM
