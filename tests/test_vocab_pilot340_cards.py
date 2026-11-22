"""語彙パイロット第340弾の対象カード（実カード parse）。

対象は pure な enters_tapped_opponent 2件（未登録、rejects 残存）:
- dmc52-007 聖霊王エルフェウス（partial は進化元を落としている。
  旧形式の登録例 dm33-s01 と同じく types は [creature] のまま
  evolve_from {race_has: エンジェル・コマンド} を補う）
- dm24bd6-006 偽りの希望 修羅丸「終斗」（partial はキーワード
  のみ。ゲート付き常在型を足す）

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


def _cand(tid, base):
    c = dict(base)
    c.pop("source", None)
    c.pop("gaps", None)
    return c


def test_targets_still_in_rejects():
    rows = _rows()
    conv_ids = {c["id"] for c in all_cards(CONVERTED)}
    for t in ("dmc52-007", "dm24bd6-006"):
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["enters_tapped_opponent"]


def test_partial_forms():
    rows = _rows()
    p = rows["dmc52-007"]["partial"]
    assert p.get("abilities") is None
    assert "evolve_from" not in p          # partial は進化元を落とす
    cand = _cand("dmc52-007", {**p,
                               "abilities": FORM_007,
                               "evolve_from": {
                                   "race_has": "エンジェル・コマンド"}})
    d = parse_card(cand, TABLES)
    assert len(d.abilities) >= 1
    p = rows["dm24bd6-006"]["partial"]
    assert p.get("abilities") is None
    cand = _cand("dm24bd6-006", {**p, "abilities": FORM_006})
    d = parse_card(cand, TABLES)
    assert len(d.abilities) >= 1


def test_proto_forms_match():
    assert proto_card("T1030")["abilities"] == FORM_007
    assert proto_card("T1031")["abilities"] == FORM_006
