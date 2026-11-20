"""語彙パイロット第325弾の対象カード検証（提出前）。

breaks_reduction は dmr21-007 / dm23rp1-004 の純粋2件のみ
（multi-gap 行にも現れない）。両行とも partial あり。
by_product で原文照合済み。

第325弾の結論はドリフト（追加語彙なし）。breaks_add は負値を取れ、
max 合成の後に既定1を含む使う能力の値すべてへ加算され、0 未満には
ならない（core.py:976-981）。形は常在型の mod に breaks_add: -1
を置くだけ:
- 形A（dmr21-007）: {kind: static,
  affects: {owner: opp, filter: {types: [creature]}},
  mod: {breaks_add: -1}}
- 形B（dm23rp1-004）: {kind: static,
  affects: {owner: opp, filter: {types: [creature], tapped: true}},
  mod: {power: -5000, breaks_add: -1}}
（dm23rp1-004 のアビスの常在型 {owner: you, other: true,
filter: {race_has: アビス}} {power: 5000, grant: [powered_breaker]}
は partial どおり既存形。keywords は [triple_breaker, abyss_rush]。
dmr21-007 の keywords は [blocker, triple_breaker]。
「マナゾーンに置く時、このカードはタップして置く」はデータモデルに
無く text のみで再現する既存の扱い）。

ラウンド360で登録する。両 id とも real.yaml / real_akashic.yaml /
real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml の
いずれにも無く、対象 id 自体に aliases 記録も無いことを提出前に
確認済み。

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

TARGETS = ("dmr21-007", "dm23rp1-004")
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


def test_targets_not_yet_registered():
    rows = _rows()
    assert len(rows) == 2045
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10271
    assert not (ids & set(rows))          # canonical 重なり0
    for tid in TARGETS:
        # 漏れ0の前提: 正本は未登録で reject 行に残っている
        assert tid not in ids and tid in rows, tid
        assert (rows[tid].get("gaps") or []) == [GAP], tid
    # breaks_reduction はこの2件だけ（multi-gap 行にも現れない）
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(TARGETS), left


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
