"""語彙パイロット第329弾の対象カード検証（提出前）。

対象は pure な shield_placement_trigger 2件:
- dm26ex4-cho047 DARK MEMORY CONTAINER（partial あり: CIP の
  draw 2 は変換済み。canon_id は自身、aliases 無し）
- dm26rp1-tr002 楯教の求道者 ザゼ・ゼーン（partial はキーワード
  のみ。canon_id は自身で、登録時に aliases 4件
  [dm24ex3-rp3s02, dm24ex3-rp3sec03, dm24rp3-s02, dm24rp3-sec003]
  が自動記録される見込み）

第329弾の結論はドリフト（追加語彙なし）。シールド配置の誘発は
{event: move, to: shield, subject: {owner: you}} の確立形
（dm24ex3-004 等44件）。墓地で機能する誘発は zone: graveyard
（217件）。墓地からの自己登場は may＋play_free {ref: self}。
「タップして出る」はキーワード enters_tapped、「自分のターン
のはじめにアンタップしない」は static {deny: [untap_at_start]}
（dmrp18-025）。タップ＋アンタップしないは tap op の
no_untap_next（dmr11-038）。「離れない」は mod {no_leave: true}
（第143弾）を duration: until_next_own_turn_start で。

ラウンド364で登録する。正本は real.yaml / real_akashic.yaml /
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

TARGETS = {"dm26ex4-cho047", "dm26rp1-tr002"}

CIP = {"kind": "trigger", "when": {"event": "move", "to": "bz",
                                   "subject": "self"},
       "effect": [{"op": "draw", "count": 2}]}

GY_TRIGGER = {"kind": "trigger", "zone": "graveyard",
              "when": {"event": "move", "to": "shield",
                       "subject": {"owner": "you"}},
              "effect": [{"op": "may",
                          "body": [{"op": "play_free",
                                    "select": {"ref": "self"}}]}]}

FORM_047 = [CIP, GY_TRIGGER]

NO_UNTAP = {"kind": "static", "affects": "self",
            "mod": {"deny": ["untap_at_start"]}}

MODAL = {"op": "modal", "count": 1, "modes": [
    [{"op": "draw", "count": 1}],
    [{"op": "choose",
      "select": {"zone": "bz", "owner": "opp",
                 "filter": {"types": ["creature"]}},
      "as": "chosen"},
     {"op": "tap", "select": {"ref": "chosen"},
      "no_untap_next": True}],
    [{"op": "modify", "select": {"ref": "self"},
      "mod": {"no_leave": True},
      "duration": "until_next_own_turn_start"}],
]}

SHIELD_TRIGGER = {"kind": "trigger",
                  "when": {"event": "move", "to": "shield",
                           "subject": {"owner": "you"}},
                  "effect": [{"op": "untap", "select": {"ref": "self"}},
                             MODAL]}

FORM_TR002 = [NO_UNTAP, SHIELD_TRIGGER]


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_not_yet_registered():
    rows = _rows()
    assert len(rows) == 2038
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10277
    assert not (ids & set(rows))          # canonical 重なり0
    # 漏れ0の前提: 正本は未登録で reject 行に残っている
    assert not (TARGETS & ids) and TARGETS <= set(rows)
    for t in TARGETS:
        assert rows[t].get("gaps") == ["shield_placement_trigger"]
    left = {rid for rid, r in rows.items()
            if "shield_placement_trigger" in (r.get("gaps") or [])}
    assert left == TARGETS, left


def test_proto_forms_match():
    c998 = proto_card("T998")
    assert c998["abilities"] == FORM_047
    d = parse_card(c998, TABLES)
    assert len(d.abilities) == 3
    c999 = proto_card("T999")
    assert c999["abilities"] == FORM_TR002
    assert c999["keywords"] == ["blocker", "double_breaker",
                                "enters_tapped"]
    d = parse_card(c999, TABLES)
    assert len(d.abilities) >= 3
