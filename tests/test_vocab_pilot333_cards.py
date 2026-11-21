"""語彙パイロット第333弾の対象カード検証（proto 形）。

対象は pure な power_transfer 2件で、ラウンド368で登録済み:
- dm24rp4-045 ブルーアイズ・ドラゴンフライ（partial は
  キーワード powered_breaker のみ。本弾で trigger を構成。
  aliases 無し）
- dmrp11-zs01 零（partial はキーワードのみ。攻撃時 trigger＋
  ターン終わり trigger＋零龍がいる間のコスト軽減 static を構成。
  aliases 無し）

結論はエンジン拡張（power mod の amount に式を許可。第333弾の
本体テスト参照）: op_modify の _bake_refs が生成時に
{power_of: {ref: 名前}} をリテラルへ固定する。常在型に直接
書くと chars が整数を前提とするため使えない（生成時ベイク専用）。

power_transfer は残り0件でファミリー解消。

確立形:
- dm24rp4-045: trigger {when: {event: move, to: bz,
  subject: {owner: you, filter: {types: [creature], cost_ge: 6}}},
  effect: [modify {select: {ref: event.subject},
  mod: {power: {amount: {power_of: {ref: self}}}},
  duration: until_next_own_turn_start}]}
- dmrp11-zs01: 攻撃時 trigger で choose {as: victim} し、
  modify self {power: {amount: {power_of: {ref: victim}}}}
  （end_of_turn）→ modify victim {power_set: 0}（先に吸い上げて
  から 0 にする）。ターン終わりの手札破棄は discard
  {chooser: opp}。コスト軽減は static {affects: {zone: hand,
  owner: you, filter: {civs: [darkness]}},
  if: {exists: {race_has: 零龍}}, mod: {cost: -1, cost_min: 0}}
  （「自分の零龍」は種族参照。発生源は場の零自身）。

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

TRIGGER_045 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "you",
                         "filter": {"types": ["creature"],
                                    "cost_ge": 6}}},
    "effect": [{"op": "modify", "select": {"ref": "event.subject"},
                "mod": {"power": {"amount": {"power_of": {"ref": "self"}}}},
                "duration": "until_next_own_turn_start"}]}

TRANSFER = {
    "kind": "trigger", "when": {"event": "attack", "subject": "self"},
    "effect": [
        {"op": "choose",
         "select": {"zone": "bz", "owner": "opp",
                    "filter": {"types": ["creature"]}, "count": 1},
         "as": "victim"},
        {"op": "modify", "select": {"ref": "self"},
         "mod": {"power": {"amount": {"power_of": {"ref": "victim"}}}},
         "duration": "end_of_turn"},
        {"op": "modify", "select": {"ref": "victim"},
         "mod": {"power_set": 0}, "duration": "end_of_turn"}]}

END_DISCARD = {
    "kind": "trigger", "when": {"event": "turn_end"},
    "if": {"is_turn": "you"},
    "effect": [{"op": "discard",
                "select": {"zone": "hand", "owner": "opp",
                           "chooser": "opp", "count": 1}}]}

COST_CUT = {
    "kind": "static",
    "affects": {"zone": "hand", "owner": "you",
                "filter": {"civs": ["darkness"]}},
    "if": {"exists": {"zone": "bz", "owner": "you",
                      "filter": {"race_has": "零龍"}}},
    "mod": {"cost": -1, "cost_min": 0}}

FORM_045 = [TRIGGER_045]
FORM_0S01 = [TRANSFER, END_DISCARD, COST_CUT]


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_registered():
    rows = _rows()
    assert len(rows) == 2028
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10286
    assert not (ids & set(rows))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dm24rp4-045")
    assert c is not None
    assert c["abilities"] == FORM_045
    assert not (c.get("source") or {}).get("unsupported")
    assert not (c.get("source") or {}).get("aliases")
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = _conv_cache.find(CONVERTED, "dmrp11-zs01")
    assert c is not None
    assert c["abilities"] == FORM_0S01
    assert not (c.get("source") or {}).get("unsupported")
    assert not (c.get("source") or {}).get("aliases")
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
    left = {rid for rid, r in rows.items()
            if "power_transfer" in (r.get("gaps") or [])}
    assert left == set(), left


def test_proto_forms_match():
    c = proto_card("T1010")
    assert c["abilities"] == FORM_045
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = proto_card("T1011")
    assert c["abilities"] == FORM_0S01
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
