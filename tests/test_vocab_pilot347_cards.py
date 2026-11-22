"""語彙パイロット第347弾の対象カード（実カード parse）。

対象は pure な up_to_cost_reduction 3件のうち2件（未登録、
rejects 残存）:
- dmbd02-014 西南の超人（partial はセイバー身代わりを持ち、
  コスト常在型だけが欠けていた）
- dm39-018 大地幻獣ガガマル（partial は能力を持たない）

dm23rp4x-tf03 は対象外（partial が完全に空で登録の基礎が
ないため rejects に残る）。

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

COST_014 = {
    "kind": "static",
    "affects": {"zone": "hand", "owner": "you",
                "filter": {"races": ["ジャイアント"]}},
    "mod": {"cost": -2},
}
SABER_014 = {
    "kind": "replace", "optional": True,
    "when": {"event": "move", "to": "graveyard", "reason": "destroy",
             "subject": {"owner": "you",
                         "filter": {"races": ["ジャイアント"]},
                         "other": True}},
    "instead": [{"op": "destroy", "select": {"ref": "self", "count": 1}}],
}
COST_018 = {
    "kind": "static",
    "affects": {"zone": "mana", "owner": "you",
                "filter": {"types": ["creature"],
                           "keyword": "summon_from_mana"}},
    "mod": {"cost": -2, "cost_min": 1},
}

FORM_014 = [COST_014, SABER_014]
FORM_018 = [COST_018]


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
    for t in ("dmbd02-014", "dm39-018"):
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["up_to_cost_reduction"]


def test_partial_forms():
    rows = _rows()
    p = rows["dmbd02-014"]["partial"]
    assert p["abilities"] == [SABER_014]
    d = parse_card(_cand("dmbd02-014", {**p, "abilities": FORM_014}),
                   TABLES)
    assert len(d.abilities) >= 2
    p = rows["dm39-018"]["partial"]
    assert not p.get("abilities")
    d = parse_card(_cand("dm39-018", {**p, "abilities": FORM_018}),
                   TABLES)
    assert len(d.abilities) >= 1


def test_proto_forms_match():
    assert proto_card("T1044")["abilities"] == FORM_014
    assert proto_card("T1045")["abilities"] == FORM_018
