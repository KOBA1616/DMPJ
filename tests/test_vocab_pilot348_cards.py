"""語彙パイロット第348弾の対象カード（実カード parse）。

対象は pure な invasion_zero 3件すべて（未登録、rejects 残存）:
- dmbd21-018 ZEROの侵略 ブラックアウト（partial は能力を
  持たない。攻撃時誘発も含め全体を組む）
- dmd35-011 ZEROの暴走 デッドリー・ハイウェイ（partial は
  Dスイッチ誘発を持ち、侵略ZERO だけが欠けていた）
- promoy15-035 禁断の月 ドキンダムーン（partial は CIP と
  Dスイッチ誘発を持ち、侵略ZERO だけが欠けていた）

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

ZERO = {
    "kind": "trigger", "zone": "hand",
    "when": {"event": "turn_end"},
    "if": {"all": [{"is_turn": "opp"},
                   {"cmp": [{"turn_count": {"kind": "enter_unpaid",
                                            "owner": "opp",
                                            "filter": {"types": ["creature"]}}},
                            ">=", 1]}]},
    "effect": [{"op": "may",
                "body": [{"op": "move", "select": {"ref": "self"},
                          "to": "bz", "reason": "put"}]}],
}
ATK_018 = {
    "kind": "trigger",
    "when": {"event": "attack", "subject": "self"},
    "if": {"exists": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["d2_field"]}}},
    "effect": [{"op": "destroy",
                "select": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"]},
                           "extremal": "max_power", "count": 1}}],
}
DSW_011 = {
    "kind": "trigger", "dswitch": True,
    "when": {"event": "turn_start", "player": "you"},
    "effect": [{"op": "may",
                "body": [{"op": "dswitch"},
                         {"op": "destroy",
                          "select": {"zone": "bz", "owner": "opp",
                                     "filter": {"types": ["creature"],
                                                "tapped": True},
                                     "count": 1}}]}],
}
CIP_035 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "mill", "owner": "you", "count": 2}],
}
DSW_035 = {
    "kind": "trigger", "dswitch": True,
    "when": {"event": "turn_start", "player": "you"},
    "effect": [{"op": "may",
                "body": [{"op": "dswitch"},
                         {"op": "move",
                          "select": {"zone": "graveyard", "owner": "you",
                                     "filter": {"race_has": "ソニック・コマンド"},
                                     "count": 1},
                          "to": "bz", "reason": "put"}]}],
}

FORM_018 = [ZERO, ATK_018]
FORM_011 = [ZERO, DSW_011]
FORM_035 = [ZERO, CIP_035, DSW_035]


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
    for t in ("dmbd21-018", "dmd35-011", "promoy15-035"):
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["invasion_zero"]


def test_partial_forms():
    rows = _rows()
    p = rows["dmbd21-018"]["partial"]
    assert not p.get("abilities")
    d = parse_card(_cand("dmbd21-018", {**p, "abilities": FORM_018}),
                   TABLES)
    assert len(d.abilities) >= 2
    p = rows["dmd35-011"]["partial"]
    assert p["abilities"] == [DSW_011]
    d = parse_card(_cand("dmd35-011", {**p, "abilities": FORM_011}),
                   TABLES)
    assert len(d.abilities) >= 2
    p = rows["promoy15-035"]["partial"]
    assert p["abilities"] == [CIP_035, DSW_035]
    d = parse_card(_cand("promoy15-035", {**p, "abilities": FORM_035}),
                   TABLES)
    assert len(d.abilities) >= 3


def test_proto_forms_match():
    assert proto_card("T1046")["abilities"] == FORM_018
    assert proto_card("T1047")["abilities"] == FORM_011
    assert proto_card("T1048")["abilities"] == FORM_035
