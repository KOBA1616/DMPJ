"""語彙パイロット第339弾の対象カード（実カード parse）。

対象は pure な opponent_cards_enter_tapped 2件で、
ラウンド374で登録済み:
- dmrp21-5a グーゴル ＜XENOM.Star＞（submit 時に aliases
  [dmrp21-7b, dmrp21-s5] が自動記録されたが rejects 行では
  ない。スター進化と攻撃時誘発は partial の形のまま）
- dm23ex3-006 偽りの名 スコーピオ（ターン開始の誘発は
  partial の {subject: self} 形では誘発しないため、実働形
  {event: turn_start}＋if {is_turn: you} に直して登録）

opponent_cards_enter_tapped の行は残っていない
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
# 登録形: submit の validate が「見ないで選び」を読み discard の
# select に chooser: random を補う
REG_5A = [
    {"kind": "trigger",
     "when": {"event": "attack", "subject": "self"},
     "effect": [{"op": "discard",
                 "select": {"zone": "hand", "owner": "opp",
                            "count": 1, "chooser": "random"}}]},
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


def test_targets_registered():
    rows = _rows()
    assert len(rows) <= 2011  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10303  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dmrp21-5a")
    assert c is not None and c["abilities"] == REG_5A
    assert c["keywords"] == ["double_breaker", "opp_mana_tapped"]
    assert c.get("star") is True
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == [
        "dmrp21-7b", "dmrp21-s5"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 2
    c = _conv_cache.find(CONVERTED, "dm23ex3-006")
    assert c is not None and c["abilities"] == FORM_006
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 4
    left = {rid for rid, r in rows.items()
            if "opponent_cards_enter_tapped" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


def test_proto_forms_match():
    assert proto_card("T1028")["abilities"] == FORM_5A
    assert proto_card("T1029")["abilities"] == FORM_006
