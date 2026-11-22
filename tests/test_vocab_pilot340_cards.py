"""語彙パイロット第340弾の対象カード（実カード parse）。

対象は pure な enters_tapped_opponent 2件で、ラウンド375で登録済み:
- dmc52-007 聖霊王エルフェウス（submit 時に aliases [dm14-001]
  が自動記録されたが rejects 行ではない。進化元は partial が
  落としていたため dm33-s01 と同形式で補って登録）
- dm24bd6-006 偽りの希望 修羅丸「終斗」（first_time 誘発）

enters_tapped_opponent の行は残っていない（ファミリー解消）。

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

FORM_007 = [
    {"kind": "static",
     "affects": {"zone": "bz", "owner": "opp",
                 "filter": {"types": ["creature"]}},
     "mod": {"grant": ["enters_tapped"]}},
]

FORM_006 = [
    {"kind": "trigger", "first_time": True,
     "when": {"event": "move", "to": "bz",
              "subject": {"owner": "opp",
                          "filter": {"types": ["creature"]}}},
     "effect": [{"op": "tap", "select": {"ref": "event.subject"}}]},
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
    assert len(rows) == 2009
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10305
    assert not (ids & set(rows))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dmc52-007")
    assert c is not None and c["abilities"] == FORM_007
    assert c["evolve_from"] == {"race_has": "エンジェル・コマンド"}
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == ["dm14-001"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = _conv_cache.find(CONVERTED, "dm24bd6-006")
    assert c is not None and c["abilities"] == FORM_006
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    left = {rid for rid, r in rows.items()
            if "enters_tapped_opponent" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


def test_proto_forms_match():
    assert proto_card("T1030")["abilities"] == FORM_007
    assert proto_card("T1031")["abilities"] == FORM_006
