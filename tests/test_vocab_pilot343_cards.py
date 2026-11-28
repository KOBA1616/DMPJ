"""語彙パイロット第343弾の対象カード（実カード parse）。

対象は pure な first_entry_tapped_per_turn 2件で、ラウンド378で解消:
- dm26ex4-cho001 アルカディアス・モモキング（正本、登録済み）
- dm26sd1-o002f（非正本。正本 cho001 の aliases として解消され、
  submit は「取得済みの原文に無いID」で弾いた。第365弾と同型）

first_entry_tapped_per_turn の行は残っていない（ファミリー解消）。

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


def test_targets_registered():
    rows = _rows()
    assert len(rows) <= 2003  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10310  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dm26ex4-cho001")
    assert c is not None and c["abilities"] == FORM
    assert not (c.get("source") or {}).get("unsupported")
    assert "dm26sd1-o002f" in (c.get("source") or {}).get("aliases", [])
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
    # 非正本は単独登録されず、rejects にも残っていない
    assert "dm26sd1-o002f" not in ids
    assert "dm26sd1-o002f" not in rows
    left = {rid for rid, r in rows.items()
            if "first_entry_tapped_per_turn" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


def test_proto_forms_match():
    assert proto_card("T1036")["abilities"] == FORM
