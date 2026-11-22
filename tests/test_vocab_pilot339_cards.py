"""語彙パイロット第339弾の対象カード（実カード parse）。

対象は pure な opponent_cards_enter_tapped 2件（未登録、
rejects 残存）:
- dmrp21-5a グーゴル ＜XENOM.Star＞（partial はスター進化の
  フィールドと攻撃時誘発を持ち、常在型だけが欠けていた）
- dm23ex3-006 偽りの名 スコーピオ（partial は裏向き化の誘発を
  持ち、水晶武装4の常在型だけが欠けていた）

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

CRYSTAL4 = {"cmp": [{"count": {"zone": "mana", "owner": "you",
                               "filter": {"face_down": True}}},
                     ">=", 4]}

FORM_5A = [
    {"kind": "trigger",
     "when": {"event": "attack", "subject": "self"},
     "effect": [{"op": "discard",
                 "select": {"zone": "hand", "owner": "opp",
                            "count": 1}}]},
    {"kind": "static", "affects": {"zone": "bz", "owner": "opp"},
     "mod": {"grant": ["enters_tapped"]}},
]

FORM_006 = [
    {"kind": "trigger",
     "when": {"event": "move", "to": "bz", "subject": "self"},
     "effect": [{"op": "may", "body": [
         {"op": "flip_down",
          "select": {"zone": "mana", "owner": "you", "count": 1}}]}]},
    {"kind": "trigger",
     "when": {"event": "turn_start"},
     "if": {"is_turn": "you"},
     "effect": [{"op": "may", "body": [
         {"op": "flip_down",
          "select": {"zone": "mana", "owner": "you", "count": 1}}]}]},
    {"kind": "static", "affects": {"zone": "bz", "owner": "opp"},
     "if": CRYSTAL4, "mod": {"grant": ["enters_tapped"]}},
    {"kind": "static", "affects": "self",
     "if": CRYSTAL4, "mod": {"grant": ["opp_mana_tapped"]}},
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
    for t in ("dmrp21-5a", "dm23ex3-006"):
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["opponent_cards_enter_tapped"]


def test_partial_forms():
    rows = _rows()
    p = rows["dmrp21-5a"]["partial"]
    assert p["abilities"] == FORM_5A[:1]        # 攻撃時誘発は既存
    assert p["keywords"] == ["double_breaker"]
    cand = _cand("dmrp21-5a", {**p,
                               "abilities": FORM_5A,
                               "keywords": ["double_breaker",
                                            "opp_mana_tapped"]})
    d = parse_card(cand, TABLES)
    assert len(d.abilities) >= 2
    p = rows["dm23ex3-006"]["partial"]
    assert p["abilities"][0] == FORM_006[0]     # 出た時は既存
    # partial のターン開始誘発は {subject: self} 形だが、turn_start
    # レコードに subject は無く決して誘発しない（dm22-012 の
    # {event: turn_start}＋if {is_turn} が実働形。第339弾で実測）
    assert p["abilities"][1]["when"] == {"event": "turn_start",
                                         "subject": "self"}
    assert p["abilities"][1]["effect"] == FORM_006[1]["effect"]
    cand = _cand("dm23ex3-006", {**p, "abilities": FORM_006})
    d = parse_card(cand, TABLES)
    assert len(d.abilities) >= 4


def test_proto_forms_match():
    assert proto_card("T1028")["abilities"] == FORM_5A
    assert proto_card("T1029")["abilities"] == FORM_006
