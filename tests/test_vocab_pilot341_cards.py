"""語彙パイロット第341弾の対象カード（実カード parse）。

対象は pure な each_player_keeps_one_creature 2件（未登録、
rejects 残存）:
- dm24bd6-003（partial は水晶武装の常在型を持ち、出た時だけが
  欠けていた）
- dm23bd5-001（partial はシールドが離れた時の first_time 誘発と
  「可能なら攻撃する」の require 常在型を持ち、出た時だけが
  欠けていた）

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

CRYSTAL_STATIC = {
    "kind": "static",
    "affects": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}},
    "if": {"cmp": [{"count": {"zone": "mana", "owner": "you",
                              "filter": {"face_down": True}}},
                    ">=", 4]},
    "mod": {"grant": ["blocker", "speed_attacker", "slayer"]},
}

def _choose_keep(as_name, owner, chooser=None):
    sel = {"zone": "bz", "owner": owner,
           "filter": {"types": ["creature"]}, "count": 1}
    if chooser:
        sel["chooser"] = chooser
    return {"op": "choose", "select": sel, "as": as_name}


def _rest_select():
    return {"zone": "bz", "owner": "any",
            "filter": {"types": ["creature"]}, "count": "all",
            "exclude": [{"ref": "keep_you"}, {"ref": "keep_opp"}]}


CIP_DESTROY = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [
        _choose_keep("keep_you", "you"),
        _choose_keep("keep_opp", "opp", chooser="opp"),
        {"op": "destroy", "select": _rest_select()},
    ],
}]

CIP_MANA = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [
        _choose_keep("keep_you", "you"),
        _choose_keep("keep_opp", "opp", chooser="opp"),
        {"op": "move", "select": _rest_select(),
         "to": "mana", "reason": "put"},
    ],
}]

FORM_003 = [CRYSTAL_STATIC] + CIP_DESTROY
FORM_001 = CIP_MANA  # + partial の既存2能力（下で個別に確認）


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
    for t in ("dm24bd6-003", "dm23bd5-001"):
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["each_player_keeps_one_creature"]


def test_partial_forms():
    rows = _rows()
    p = rows["dm24bd6-003"]["partial"]
    assert p["abilities"] == [CRYSTAL_STATIC]     # 水晶武装は既存
    cand = _cand("dm24bd6-003", {**p, "abilities": FORM_003})
    d = parse_card(cand, TABLES)
    assert len(d.abilities) >= 2
    p = rows["dm23bd5-001"]["partial"]
    assert len(p["abilities"]) == 2               # 誘発＋require は既存
    cand = _cand("dm23bd5-001",
                 {**p, "abilities": p["abilities"] + CIP_MANA})
    d = parse_card(cand, TABLES)
    assert len(d.abilities) >= 3


def test_proto_forms_match():
    assert proto_card("T1032")["abilities"] == FORM_003
    assert proto_card("T1033")["abilities"] == CIP_MANA
