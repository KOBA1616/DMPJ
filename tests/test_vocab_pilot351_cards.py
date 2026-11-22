"""語彙パイロット第351弾の対象カード（実カード parse）。

対象は pure な battle_power_against_specific_race 2件すべて
（未登録、rejects 残存）:
- dm08-006 光器サーシャ
- dm16-021 光器スヴェータ
（いずれも partial は能力を持たず、全体を組む）

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


def test_targets_still_in_rejects():
    rows = _rows()
    conv_ids = {c["id"] for c in all_cards(CONVERTED)}
    for t in ("dm08-006", "dm16-021"):
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["battle_power_against_specific_race"]


def test_partial_forms():
    rows = _rows()
    for tid, form in (("dm08-006", FORM_006), ("dm16-021", FORM_021)):
        p = rows[tid]["partial"]
        assert not p.get("abilities")
        d = parse_card(_cand(tid, {**p, "abilities": form}), TABLES)
        assert len(d.abilities) >= 1


def test_proto_forms_match():
    assert proto_card("T1056")["abilities"] == FORM_006
    assert proto_card("T1057")["abilities"] == FORM_021
