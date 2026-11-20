"""語彙パイロット第304弾の対象カード検証（ラウンド339で登録済み）。

evolution_cross_gear 純粋3件（dmc42-017 / dmc45-017 /
dm17-s05）と、第2ギャップ evolution_base_any_race が第232弾で
実装済みの dmc42-001 は、ラウンド339で登録された。ここでは
登録形が第304弾の確立形と完全一致し、対象行が rejects から
解消したことを固定する。実挙動は第304弾本体（プロト）と
ラウンド339 cards（登録カード自身）で固定済み。

正本判定（ラウンド339で identity を実データ照合）:
- 対象4件はいずれも canon_id が自身＝独立正本。
- canon_id(dm17-003) = dmc42-017、canon_id(promoy4-024) =
  dmc42-001 で、partial の source.aliases と一致する。alias は
  登録カードの source.aliases に記録されただけ（どちらの
  alias にも reject 行は元々無かった）。

確立形:
- 共通（純粋3件）: types は [cross_gear, evolution]、
  evolve_from は本文の進化条件そのもの（civs は any-of 照合）。
- dmc42-017: evolve_from {civs: [water, darkness]}。残りの
  能力は partial の形（crossed への power +2000、攻撃時
  誘発）のまま。
- dmc45-017: evolve_from {races: [サムライ]} ＋ クルー・
  ブレイカーを static {affects: crossed, mod: {breaks:
  {count: {zone: bz, owner: you, other: true, filter:
  {race_has: サムライ, types: [creature]}}}}} で追加。
- dm17-s05: evolve_from {civs: [light, nature]}。残りの
  能力は partial の形のまま。
- dmc42-001: types は [cross_gear] のまま。abilities =
  [static {affects: crossed, mod: {allow: [evolve_base_any]}},
   static {affects: self, mod: {allow: [evolve_civ_any]}}]。
- text は reject 行の正式本文（partial の text は
  「マナゾーンに置く時」行が欠けていた）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活
するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
import _conv_cache  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
PURE = ("dmc42-017", "dmc45-017", "dm17-s05")
EXTRA = "dmc42-001"

CREW_STATIC = {"kind": "static", "affects": "crossed",
               "mod": {"breaks": {"count": {
                   "zone": "bz", "owner": "you", "other": True,
                   "filter": {"race_has": "サムライ",
                              "types": ["creature"]}}}}}

STATICS_001 = [
    {"kind": "static", "affects": "crossed",
     "mod": {"allow": ["evolve_base_any"]}},
    {"kind": "static", "affects": "self",
     "mod": {"allow": ["evolve_civ_any"]}}]


def _reject_rows():
    rows = {}
    for line in open(ROOT / "data/cards/raw/rejects.jsonl", encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            rows[r["id"]] = r
    return rows


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_targets_registered_in_pilot304_forms():
    rows = _reject_rows()
    for cid in PURE + (EXTRA,):
        assert cid not in rows, cid          # rejects から外れた
        c = _conv(cid)
        assert c is not None, cid            # converted に登録済み
        assert not (c.get("source") or {}).get("unsupported"), cid
        parse_card(c, TABLES)
    d = parse_card(_conv("dmc42-017"), TABLES)
    assert d.types == ["cross_gear", "evolution"]
    assert d.evolve_from == {"civs": ["water", "darkness"]}
    c = _conv("dmc45-017")
    d = parse_card(c, TABLES)
    assert d.evolve_from == {"races": ["サムライ"]}
    assert CREW_STATIC in c["abilities"]
    d = parse_card(_conv("dm17-s05"), TABLES)
    assert d.evolve_from == {"civs": ["light", "nature"]}
    c = _conv(EXTRA)
    d = parse_card(c, TABLES)
    assert d.types == ["cross_gear"]
    assert c["abilities"] == STATICS_001
    # text は正式本文へ復元済み（「マナゾーンに置く時」行を含む）
    assert _conv("dmc42-017")["text"].startswith("マナゾーンに置く時")
    assert _conv("dmc45-017")["text"].startswith("マナゾーンに置く時")
    # alias は source.aliases に記録（独立エントリではない）
    assert (_conv("dmc42-017").get("source") or {}).get("aliases") == ["dm17-003"]
    assert (_conv(EXTRA).get("source") or {}).get("aliases") == ["promoy4-024"]
    assert _conv("dm17-003") is None
    assert _conv("promoy4-024") is None


def test_evolution_cross_gear_targets_cleared():
    rows = _reject_rows()
    pure = {rid for rid, r in rows.items()
            if set(r.get("gaps") or []) <= {"evolution_cross_gear",
                                            "evolution_base_any_race"}
            and r.get("gaps")}
    assert pure == set(), pure
    # ギャップ名自体は他ギャップ併記の3行に残る
    holders = {rid for rid, r in rows.items()
               if "evolution_cross_gear" in (r.get("gaps") or [])}
    assert holders == {"dmc66-034", "dm17-004", "dm17-s04"}, holders
