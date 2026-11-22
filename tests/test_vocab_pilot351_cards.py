"""語彙パイロット第351弾の対象カード（実カード parse）。

対象は pure な battle_power_against_specific_race 2件すべてで、
ラウンド386で登録:
- dm08-006 光器サーシャ
- dm16-021 光器スヴェータ
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

DRAGON_BLOCK = {
    "kind": "static", "affects": "self",
    "mod": {"allow": [{"action": "block",
                       "other": {"race_has": "ドラゴン"}}]},
}
BATTLE_006 = {
    "kind": "static", "affects": "self",
    "mod": {"battle_power": {"amount": 6000,
                             "opponent_filter": {"race_has": "ドラゴン"}}},
}
BATTLE_021 = {
    "kind": "static", "affects": "self",
    "mod": {"battle_power": {"amount": 4000,
                             "opponent_filter": {"any_of": [
                                 {"race_has": "デーモン・コマンド"},
                                 {"race_has": "ドラゴン"}]}}},
}

FORM_006 = [DRAGON_BLOCK, BATTLE_006]
FORM_021 = [BATTLE_021]


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
    assert len(rows) == 1984
    conv = all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10328
    assert not (ids & set(rows))          # canonical 重なり0
    for tid, form in (("dm08-006", FORM_006), ("dm16-021", FORM_021)):
        c = next(x for x in conv if x["id"] == tid)
        assert c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    left = {rid for rid, r in rows.items()
            if "battle_power_against_specific_race" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


def test_registered_parse():
    conv = all_cards(CONVERTED)
    for tid in ("dm08-006", "dm16-021"):
        c = next(x for x in conv if x["id"] == tid)
        d = parse_card(c, TABLES)
        assert len(d.abilities) >= 1


def test_proto_forms_match():
    assert proto_card("T1056")["abilities"] == FORM_006
    assert proto_card("T1057")["abilities"] == FORM_021
