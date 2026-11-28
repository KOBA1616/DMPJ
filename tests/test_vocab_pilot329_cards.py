"""語彙パイロット第329弾の対象カード検証（登録形）。

対象は pure な shield_placement_trigger 2件:
- dm26ex4-cho047 DARK MEMORY CONTAINER（partial あり: CIP の
  draw 2 は変換済み。canon_id は自身、登録時に aliases 3件
  [dm25ex3-055, dm25rp2-048, promoy25-051] が自動記録された）
- dm26rp1-tr002 楯教の求道者 ザゼ・ゼーン（partial はキーワード
  のみ。canon_id は自身、登録時に aliases 4件
  [dm24ex3-rp3s02, dm24ex3-rp3sec03, dm24rp3-s02, dm24rp3-sec003]
  が自動記録された）

第329弾の結論はドリフト（追加語彙なし）。シールド配置の誘発は
{event: move, to: shield, subject: {owner: you}} の確立形
（dm24ex3-004 等44件）。墓地で機能する誘発は zone: graveyard
（217件）。墓地からの自己登場は may＋move {ref: self} to: bz
reason: put（「出す」は召喚ではないため play_free ではなく
move/put。submit のバリデータ警告で確認し、登録後に converted
側も同形へ修正済み）。「タップして出る」はキーワード
enters_tapped、「自分のターンのはじめにアンタップしない」は
static {deny: [untap_at_start]}（dmrp18-025）。タップ＋アンタップ
しないは tap op の no_untap_next（dmr11-038）。「離れない」は
mod {no_leave: true}（第143弾）を duration:
until_next_own_turn_start で。

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
                          "body": [{"op": "move",
                                    "select": {"ref": "self"},
                                    "to": "bz", "reason": "put"}]}]}

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


def test_targets_registered():
    rows = _rows()
    assert len(rows) <= 2036  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10279  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    assert TARGETS <= ids and not (TARGETS & set(rows))
    c = _conv_cache.find(CONVERTED, "dm26ex4-cho047")
    assert c is not None
    assert c["abilities"] == FORM_047
    assert c["keywords"] == ["blocker"]
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == [
        "dm25ex3-055", "dm25rp2-048", "promoy25-051"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 3
    c = _conv_cache.find(CONVERTED, "dm26rp1-tr002")
    assert c is not None
    assert c["abilities"] == FORM_TR002
    assert c["keywords"] == ["blocker", "double_breaker",
                             "enters_tapped"]
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == [
        "dm24ex3-rp3s02", "dm24ex3-rp3sec03", "dm24rp3-s02",
        "dm24rp3-sec003"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
    # shield_placement_trigger は残り0件でファミリー解消
    left = {rid for rid, r in rows.items()
            if "shield_placement_trigger" in (r.get("gaps") or [])}
    assert left == set(), left


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
