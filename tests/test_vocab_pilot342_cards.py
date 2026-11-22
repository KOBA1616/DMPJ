"""語彙パイロット第342弾の対象カード（実カード parse）。

対象は pure な battle_power_grant 2件（未登録、rejects 残存）:
- dmr11-016 破戒のインガ シャンツァイ（partial はコスト軽減の
  常在型を持ち、バトル中の付与だけが欠けていた）
- dm23rp2x-006 ボルシャック・ノブリス・ドラゴン（partial の
  コスト軽減の常在型は条件が race_has に化けた壊れた形のため、
  原文どおりの形に直して使う。メクレイド誘発は partial のまま）

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

GRANT_016 = [{
    "kind": "static",
    "affects": {"owner": "you",
                "filter": {"any_of": [{"race_has": "オラクル"},
                                      {"race_has": "ゴッド"}]}},
    "mod": {"battle_power": {"amount": 3000}},
}]

GRANT_006 = [{
    "kind": "static",
    "affects": {"owner": "you", "filter": {"race_has": "アーマード"}},
    "mod": {"battle_power": {"amount": 3000}},
}]

COST_006_FIXED = {
    "kind": "static", "zone": "hand", "affects": "self",
    "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                              "filter": {"civs": ["fire"]}}},
                    ">=", 3]},
    "mod": {"cost": -3},
}

FORM_016 = GRANT_016   # + partial の opt_reduce（下で個別に確認）
FORM_006 = [COST_006_FIXED] + GRANT_006  # + partial のメクレイド誘発


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
    for t in ("dmr11-016", "dm23rp2x-006"):
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["battle_power_grant"]


def test_partial_forms():
    rows = _rows()
    p = rows["dmr11-016"]["partial"]
    assert len(p["abilities"]) == 1               # opt_reduce は既存
    cand = _cand("dmr11-016",
                 {**p, "abilities": p["abilities"] + GRANT_016})
    d = parse_card(cand, TABLES)
    assert len(d.abilities) >= 2
    p = rows["dm23rp2x-006"]["partial"]
    garbled = p["abilities"][0]
    assert "エレメントが3つ以上あればこの" in \
        json.dumps(garbled, ensure_ascii=False)   # 化け形であること
    fixed = [COST_006_FIXED, p["abilities"][1]] + GRANT_006
    cand = _cand("dm23rp2x-006", {**p, "abilities": fixed})
    d = parse_card(cand, TABLES)
    assert len(d.abilities) >= 3


def test_proto_forms_match():
    assert proto_card("T1034")["abilities"] == GRANT_016
    assert proto_card("T1035")["abilities"] == GRANT_006
