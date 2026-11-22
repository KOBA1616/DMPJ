"""語彙パイロット第335弾の対象カード（実カード parse）。

対象は pure な per_card_tap_or_untap 3件で、ラウンド370で登録済み:
- dm25bd2-015 清浄の精霊ウル（partial はキーワードのみ。
  本弾で choose＋modal を構成。submit 時に aliases
  [dmd32-007, dmex11-015, dmpcd01-t10] が自動記録されたが
  rejects 行ではない）
- dm24rp2-051 粛清者ゴットハルト（partial はキーワードのみ。
  本弾で repeat＋choose＋modal を構成）
- dm25-002 超鎧亜キングダム・ゲオルグ（partial は
  evolve_from {multicolor: true} とキーワードを持ち、攻撃時
  誘発だけが欠けていた。本弾で may＋choose＋modal を構成）

per_card_tap_or_untap の行は残っていない（ファミリー解消）。

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

CHOOSE_1 = {"op": "choose",
            "select": {"zone": "bz", "owner": "any",
                       "filter": {"types": ["creature"]}, "count": 1},
            "as": "target"}
MODAL_TU = {"op": "modal", "modes": [
    [{"op": "tap", "select": {"ref": "target"}}],
    [{"op": "untap", "select": {"ref": "target"}}]]}

FORM_015 = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [CHOOSE_1, MODAL_TU],
}]

CHOOSE_UP2 = {"op": "choose",
              "select": {"zone": "bz", "owner": "any",
                         "filter": {"types": ["creature"]},
                         "count": 1, "up_to": True},
              "as": "target"}

FORM_051 = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "repeat", "times": 2,
                "body": [CHOOSE_UP2, MODAL_TU]}],
}]

CHOOSE_E = {"op": "choose",
            "select": {"zone": "bz", "owner": "any",
                       "filter": {"types": ["creature"],
                                  "evolution": False}, "count": 1},
            "as": "target"}

FORM_002 = [{
    "kind": "trigger",
    "when": {"event": "attack", "subject": "self"},
    "effect": [{"op": "may", "body": [CHOOSE_E, MODAL_TU]}],
}]


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_registered():
    rows = _rows()
    assert len(rows) == 2023
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10291
    assert not (ids & set(rows))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dm25bd2-015")
    assert c is not None
    assert c["abilities"] == FORM_015
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == [
        "dmd32-007", "dmex11-015", "dmpcd01-t10"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = _conv_cache.find(CONVERTED, "dm24rp2-051")
    assert c is not None
    assert c["abilities"] == FORM_051
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = _conv_cache.find(CONVERTED, "dm25-002")
    assert c is not None
    assert c["abilities"] == FORM_002
    assert c["evolve_from"] == {"multicolor": True}
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    left = {rid for rid, r in rows.items()
            if "per_card_tap_or_untap" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


def test_proto_forms_match():
    c = proto_card("T1015")
    assert c["abilities"] == FORM_015
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = proto_card("T1016")
    assert c["abilities"] == FORM_051
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = proto_card("T1017")
    assert c["abilities"] == FORM_002
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
