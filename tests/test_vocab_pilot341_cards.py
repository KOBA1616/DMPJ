"""語彙パイロット第341弾の対象カード（実カード parse）。

対象は pure な each_player_keeps_one_creature 2件で、
ラウンド376で登録済み:
- dm24bd6-003 偽りのコード シャーロック（partial の水晶武装
  常在型＋出た時の破壊）
- dm23bd5-001 煉獄大帝 キング・ロマノフ（partial の2能力＋
  出た時のマナ送り）

each_player_keeps_one_creature の行は残っていない
（ファミリー解消）。

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


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_registered():
    rows = _rows()
    assert len(rows) <= 2007  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10307  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dm24bd6-003")
    assert c is not None and c["abilities"] == FORM_003
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 2
    c = _conv_cache.find(CONVERTED, "dm23bd5-001")
    assert c is not None
    assert c["abilities"][-1:] == CIP_MANA
    assert len(c["abilities"]) == 3
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
    left = {rid for rid, r in rows.items()
            if "each_player_keeps_one_creature" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


def test_proto_forms_match():
    assert proto_card("T1032")["abilities"] == FORM_003
    assert proto_card("T1033")["abilities"] == CIP_MANA
