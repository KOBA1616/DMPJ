"""語彙パイロット第353弾の対象カード（実カード parse）。

対象は pure な trigger_when_opponent_plays_without_paying
2件すべてで、ラウンド388で登録:
- dm22rp2x-020 チッタ・ペロルの冠
- dm23rp2x-033 ゼンツー
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

TRIG_020 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp",
                         "filter": {"types": ["creature", "tamaseed"]}},
             "unpaid": True},
    "if": {"is_turn": "opp"},
    "effect": [
        {"op": "may", "body": [
            {"op": "destroy", "select": {"ref": "self"}},
            {"op": "draw", "count": 1},
            {"op": "may", "body": [
                {"op": "choose",
                 "select": {"zone": "hand", "owner": "you",
                            "filter": {"types": ["creature"],
                                       "civs": ["fire"], "cost_le": 5},
                            "count": 1},
                 "as": "pc"},
                {"op": "move", "select": {"ref": "pc"},
                 "to": "bz", "reason": "put"},
            ]},
        ]},
    ],
}
TRIG_033 = {
    "kind": "trigger", "once_per_turn": True,
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp"}, "unpaid": True},
    "effect": [{"op": "may", "body": [
        {"op": "mekurade",
         "filter": {"race_has": "マジック"}, "cost_le": 5}]}],
}

FORM_020 = [TRIG_020]
FORM_033 = [TRIG_033]


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
    assert len(rows) == 1980
    conv = all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10332
    assert not (ids & set(rows))          # canonical 重なり0
    for tid, form in (("dm22rp2x-020", FORM_020),
                      ("dm23rp2x-033", FORM_033)):
        c = next(x for x in conv if x["id"] == tid)
        assert c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    pure_left = {rid for rid, r in rows.items()
                 if r.get("gaps") == [
                     "trigger_when_opponent_plays_without_paying"]}
    assert pure_left == set(), pure_left  # pure は解消


def test_registered_parse():
    conv = all_cards(CONVERTED)
    for tid in ("dm22rp2x-020", "dm23rp2x-033"):
        c = next(x for x in conv if x["id"] == tid)
        d = parse_card(c, TABLES)
        assert len(d.abilities) >= 1


def test_proto_forms_match():
    assert proto_card("T1060")["abilities"] == FORM_020
    assert proto_card("T1061")["abilities"] == FORM_033
