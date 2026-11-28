"""語彙パイロット第347弾の対象カード（実カード parse）。

対象は pure な up_to_cost_reduction 3件のうち2件で、ラウンド382で登録:
- dmbd02-014 西南の超人
- dm39-018 大地幻獣ガガマル
（登録形は意図した形と完全一致）

dm23rp4x-tf03 は対象外のまま rejects に残る（partial が
完全に空で登録の基礎がないため）。

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


def test_targets_registered():
    rows = _rows()
    assert len(rows) <= 1994  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10319  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    for tid, form in (("dmbd02-014", FORM_014),
                      ("dm39-018", FORM_018)):
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None and c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    # dm23rp4x-tf03 は対象外のまま残る
    # （後続の再変換で登録済みになってもよい）
    if "dm23rp4x-tf03" in rows:
        assert rows["dm23rp4x-tf03"].get("gaps") == ["up_to_cost_reduction"]


def test_proto_forms_match():
    assert proto_card("T1044")["abilities"] == FORM_014
    assert proto_card("T1045")["abilities"] == FORM_018
