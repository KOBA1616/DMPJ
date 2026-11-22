"""語彙パイロット第352弾の対象カード（実カード parse）。

対象は pure な optional_cost_reduction_per_count 2件すべて
（未登録、rejects 残存）:
- dm31-033 爆獣パンダ・ブーリン
- dmbd16-007 聖霊龍騎セイント・ボルシャック
  （partial の power_when 常在型はそのまま使う）

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

COST_033 = {"kind": "static", "zone": "hand", "affects": "self",
            "mod": {"cost": {"amount": -1,
                             "count": {"zone": "mana", "owner": "you",
                                       "filter": {"types": ["spell"]}}},
                    "cost_min": 1}}
COST_007 = {"kind": "static", "zone": "hand", "affects": "self",
            "mod": {"cost": {"amount": -1,
                             "count": {"zone": "graveyard", "owner": "you",
                                       "filter": {"any_of": [
                                           {"races": ["エンジェル・コマンド"]},
                                           {"races": ["アーマード・ドラゴン"]}]}}},
                    "cost_min": 1}}
POWER_WHEN_007 = {"kind": "static", "affects": "self",
                  "mod": {"power_when": {"amount": 4000,
                                         "when": "attacking"}}}

FORM_033 = [COST_033]
FORM_007 = [COST_007, POWER_WHEN_007]


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
    for t in ("dm31-033", "dmbd16-007"):
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["optional_cost_reduction_per_count"]


def test_partial_forms():
    rows = _rows()
    p = rows["dm31-033"]["partial"]
    assert not p.get("abilities")
    d = parse_card(_cand("dm31-033", {**p, "abilities": FORM_033}), TABLES)
    assert len(d.abilities) >= 1
    p = rows["dmbd16-007"]["partial"]
    assert p["abilities"] == [POWER_WHEN_007]
    d = parse_card(_cand("dmbd16-007", {**p, "abilities": FORM_007}), TABLES)
    assert len(d.abilities) >= 2


def test_proto_forms_match():
    assert proto_card("T1058")["abilities"] == FORM_033
    assert proto_card("T1059")["abilities"] == FORM_007
