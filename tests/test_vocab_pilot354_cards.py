"""語彙パイロット第354弾の対象カード（実カード parse）。

対象は pure な forced_attack_target 2件すべてで、
ラウンド389で登録:
- dm16-s03（進化クリーチャー）
- dm10-s07 不落の超人
（いずれも partial は能力を持たず全体を組んだ。
登録形は意図した形と完全一致）

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

STATIC_S03 = {"kind": "static", "affects": "self",
              "mod": {"must_be_attacked": True}}
STATIC_S07 = {
    "kind": "static", "affects": "self",
    "if": {"all": [
        {"is_turn": "opp"},
        {"exists": {"ref": "self", "filter": {"tapped": True}}},
        {"cmp": [{"turn_count": {"kind": "attack_on", "ref": "self"}},
                 "==", 0]}]},
    "mod": {"must_be_attacked": True},
}

FORM_S03 = [STATIC_S03]
FORM_S07 = [STATIC_S07]


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


def test_targets_registered():
    rows = _rows()
    assert len(rows) == 1978
    conv = all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10334
    assert not (ids & set(rows))          # canonical 重なり0
    for tid, form in (("dm16-s03", FORM_S03), ("dm10-s07", FORM_S07)):
        c = next(x for x in conv if x["id"] == tid)
        assert c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    left = {rid for rid, r in rows.items()
            if "forced_attack_target" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


def test_registered_parse():
    conv = all_cards(CONVERTED)
    for tid in ("dm16-s03", "dm10-s07"):
        c = next(x for x in conv if x["id"] == tid)
        d = parse_card(c, TABLES)
        assert len(d.abilities) >= 1


def test_proto_forms_match():
    assert proto_card("T1064")["abilities"] == FORM_S03
    assert proto_card("T1063")["abilities"] == FORM_S07
