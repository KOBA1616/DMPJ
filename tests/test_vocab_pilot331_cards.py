"""語彙パイロット第331弾の対象カード検証（登録形）。

対象は pure な name_addition 2件（いずれも partial あり）で、
ラウンド366で登録済み:
- dm23ex1-039 ボルメテウス・剣誠・ドラゴン（aliases 4件は
  partial 由来のまま source.aliases に記録）
- dm28-008 竜装 ムシャ・レジェンド（aliases 無し）

結論はドリフト（文書化）: mod の add_names はエンジン実装済み
（バンドC2 U97）だが converted の使用例が0件だった。確立形:
- 本人: {kind: static, affects: self, mod: {add_names: [名前]}}
- クロスギア: affects: crossed の mod に add_names を足す
  （dm28-008 の partial が持つ power / add_races と同居）

dm23ex1-039 の残り: G・ゼロは top-level free_if（dm23ex1-075
等。all＋cmp(count race_has サムライ >=5)＋not exists(name 自身)）、
攻撃時誘発は may＋destroy power_le 6000 の確立形。

name_addition の行は multi の dmx15-002（g_link_360 と複合）
だけが残る。

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

ADDED = "ボルメテウス・武者・ドラゴン"
OWN = "ボルメテウス・剣誠・ドラゴン"
T_ADDED = "試験用ボルメテウス・武者・ドラゴン"
T_OWN = "試験用ボルメテウス・剣誠・ドラゴン"

FREE_IF = {"all": [
    {"cmp": [{"count": {"zone": "bz", "owner": "you",
                        "filter": {"race_has": "サムライ"}}}, ">=", 5]},
    {"not": {"exists": {"zone": "bz", "owner": "you",
                        "filter": {"name": OWN}}}}]}

ATTACK_TRIGGER = {
    "kind": "trigger", "when": {"event": "attack", "subject": "self"},
    "effect": [{"op": "may", "body": [
        {"op": "destroy",
         "select": {"zone": "bz", "owner": "opp",
                    "filter": {"types": ["creature"], "power_le": 6000},
                    "count": 1}}]}]}

ADD_NAME_STATIC = {"kind": "static", "affects": "self",
                   "mod": {"add_names": [ADDED]}}

FORM_039 = [ATTACK_TRIGGER, ADD_NAME_STATIC]

GEAR_STATIC = {"kind": "static", "affects": "crossed",
               "mod": {"power": 2000,
                       "add_races": ["アーマード・ドラゴン", "サムライ"],
                       "add_names": [ADDED]}}

GEAR_TRIGGER = {
    "kind": "trigger", "when": {"event": "attack", "subject": "crossed"},
    "effect": [{"op": "may", "body": [
        {"op": "move", "select": {"zone": "shield", "owner": "you",
                                  "count": 1},
         "to": "graveyard", "reason": "put", "as": "paid"},
        {"op": "if", "cond": {"exists": {"ref": "paid"}},
         "then": [{"op": "destroy",
                   "select": {"zone": "bz", "owner": "opp",
                              "filter": {"types": ["creature"],
                                         "power_le": 6000},
                              "count": 1}}]}]}]}

FORM_008 = [GEAR_STATIC, GEAR_TRIGGER]


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_registered():
    rows = _rows()
    assert len(rows) <= 2032  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10282  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dm23ex1-039")
    assert c is not None
    assert c["free_if"] == FREE_IF
    assert c["abilities"] == FORM_039
    assert c["keywords"] == ["double_breaker"]
    assert (c.get("source") or {}).get("aliases") == \
        ["dmc45-006", "dmc55-006", "dmc59-001", "dmpcd02-a02"]
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 2
    c = _conv_cache.find(CONVERTED, "dm28-008")
    assert c is not None
    assert c["abilities"] == FORM_008
    assert not (c.get("source") or {}).get("unsupported")
    assert not (c.get("source") or {}).get("aliases")
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 2
    # name_addition は multi の dmx15-002（g_link_360 複合）だけ残る
    left = {rid for rid, r in rows.items()
            if "name_addition" in (r.get("gaps") or [])}
    assert left == {"dmx15-002"}, left


def test_proto_forms_match():
    c = proto_card("T1005")
    assert c["abilities"][0] == ATTACK_TRIGGER
    assert c["abilities"][1]["mod"] == {"add_names": [T_ADDED]}
    assert c["free_if"]["all"][0] == FREE_IF["all"][0]
    assert c["free_if"]["all"][1]["not"]["exists"]["filter"] == \
        {"name": T_OWN}
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 2
    c = proto_card("T1006")
    assert c["abilities"][0]["mod"]["add_names"] == [T_ADDED]
    assert c["abilities"][0]["mod"]["power"] == 2000
    assert c["abilities"][1] == GEAR_TRIGGER
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 2
