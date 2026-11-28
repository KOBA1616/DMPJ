"""語彙パイロット第325弾の対象カード検証（登録形）。

breaks_reduction は dmr21-007 / dm23rp1-004 の純粋2件だった
（multi-gap 行にも現れない）。両行とも partial あり。
by_product で原文照合済み。両 id とも正本で aliases 記録なし。

第325弾の結論はドリフト（追加語彙なし）。breaks_add は負値を取れ、
max 合成の後に既定1を含む使う能力の値すべてへ加算され、0 未満には
ならない（core.py:976-981）。形は常在型の mod に breaks_add: -1
を置くだけ:
- 形A（dmr21-007）: {kind: static,
  affects: {owner: opp, filter: {types: [creature]}},
  mod: {breaks_add: -1}}（keywords [blocker, triple_breaker]）
- 形B（dm23rp1-004）: {kind: static,
  affects: {owner: opp, filter: {types: [creature], tapped: true}},
  mod: {power: -5000, breaks_add: -1}}（アビスの常在型は partial
  どおり既存形。keywords [triple_breaker, abyss_rush]）

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
_conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"
TABLES = load_tables()

GAP = "breaks_reduction"

FORM_A = {"kind": "static",
          "affects": {"owner": "opp", "filter": {"types": ["creature"]}},
          "mod": {"breaks_add": -1}}
FORM_B = {"kind": "static",
          "affects": {"owner": "opp",
                      "filter": {"types": ["creature"], "tapped": True}},
          "mod": {"power": -5000, "breaks_add": -1}}
FORM_B2 = {"kind": "static",
           "affects": {"owner": "you", "other": True,
                       "filter": {"race_has": "アビス"}},
           "mod": {"power": 5000, "grant": ["powered_breaker"]}}


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_registered():
    rows = _rows()
    assert len(rows) <= 2043  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10273  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    for tid in ("dmr21-007", "dm23rp1-004"):
        assert tid in ids and tid not in rows, tid
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None
        assert not (c.get("source") or {}).get("unsupported")
        assert not (c.get("source") or {}).get("aliases")
    c007 = _conv_cache.find(CONVERTED, "dmr21-007")
    assert c007["abilities"] == [FORM_A]
    assert c007["keywords"] == ["blocker", "triple_breaker"]
    d = parse_card(c007, TABLES)
    assert FORM_A in d.abilities
    c004 = _conv_cache.find(CONVERTED, "dm23rp1-004")
    assert c004["abilities"] == [FORM_B, FORM_B2]
    assert c004["keywords"] == ["triple_breaker", "abyss_rush"]
    d = parse_card(c004, TABLES)
    assert FORM_B in d.abilities and FORM_B2 in d.abilities
    # breaks_reduction は残り0件でファミリー解消
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left


def test_proto_forms_match():
    c992 = proto_card("T992")
    assert c992["abilities"] == [FORM_A]
    assert c992["keywords"] == ["blocker", "triple_breaker"]
    d = parse_card(c992, TABLES)
    assert FORM_A in d.abilities
    c993 = proto_card("T993")
    assert c993["abilities"] == [FORM_B, FORM_B2]
    assert c993["keywords"] == ["triple_breaker", "abyss_rush"]
    d = parse_card(c993, TABLES)
    assert FORM_B in d.abilities and FORM_B2 in d.abilities
