"""語彙パイロット第342弾の対象カード（実カード parse）。

対象は pure な battle_power_grant 2件で、ラウンド377で登録済み:
- dmr11-016 破戒のインガ シャンツァイ（partial の opt_reduce＋付与）
- dm23rp2x-006 ボルシャック・ノブリス・ドラゴン（コスト軽減は
  化け形を原文どおりに直し、メクレイド誘発は partial のまま＋付与。
  submit が化け形の常在型も先頭に足して4能力で登録されたため、
  化け形側を除去して意図した3能力に直した。第374弾と同型の事故）

battle_power_grant の行は残っていない（ファミリー解消）。

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

OPT_REDUCE_016 = {
    "kind": "static", "affects": "self", "zone": "hand",
    "mod": {"opt_reduce": {"amount": 1, "per": True, "floor": 2,
                           "do": {"select": {"zone": "hand",
                                             "owner": "you",
                                             "filter": {"race_has": "ゴッド"}}}}},
}

GRANT_016 = {
    "kind": "static",
    "affects": {"owner": "you",
                "filter": {"any_of": [{"race_has": "オラクル"},
                                      {"race_has": "ゴッド"}]}},
    "mod": {"battle_power": {"amount": 3000}},
}

GRANT_006 = {
    "kind": "static",
    "affects": {"owner": "you", "filter": {"race_has": "アーマード"}},
    "mod": {"battle_power": {"amount": 3000}},
}

COST_006_FIXED = {
    "kind": "static", "zone": "hand", "affects": "self",
    "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                              "filter": {"civs": ["fire"]}}},
                    ">=", 3]},
    "mod": {"cost": -3},
}

MEKURADE_006 = {
    "kind": "trigger",
    "when": {"event": "summon", "subject": "self"},
    "effect": [{"op": "mekurade", "filter": {"race_has": "アーマード"},
                "cost_le": 8},
               {"op": "mekurade", "filter": {"race_has": "アーマード"},
                "cost_le": 8}],
}

FORM_016 = [OPT_REDUCE_016, GRANT_016]
FORM_006 = [COST_006_FIXED, MEKURADE_006, GRANT_006]


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_registered():
    rows = _rows()
    assert len(rows) == 2005
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10309
    assert not (ids & set(rows))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dmr11-016")
    assert c is not None and c["abilities"] == FORM_016
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 2
    c = _conv_cache.find(CONVERTED, "dm23rp2x-006")
    assert c is not None and c["abilities"] == FORM_006
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == \
        ["dm23rp2-006", "dm23rp2x-06x"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
    left = {rid for rid, r in rows.items()
            if "battle_power_grant" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


def test_proto_forms_match():
    assert proto_card("T1034")["abilities"] == [GRANT_016]
    assert proto_card("T1035")["abilities"] == [GRANT_006]
