"""語彙パイロット第332弾の対象カード検証（proto 形）。

対象は pure な destroyed_during_battle_trigger 2件:
- dm24rp4-070 ライラ・理・アイニー（partial はキーワードのみ。
  本弾で trigger を構成）
- dm22rp2x-026 真価と代価のチェスト（partial はシビルカウント
  2件を持ち、帰還の誘発だけが欠けていた）

結論は小さなエンジン拡張（when の battle フラグ。第332弾の
本体テスト参照）: バトルの敗者の move レコードが持つ
battle: True を、収集レコードへの伝播＋when 照合＋
Checker.when＋schema の5点で照合可能にした。

確立形:
- dm24rp4-070: {kind: trigger, when: {event: move, from: bz,
  to: graveyard, reason: destroy, battle: true, subject: self},
  effect: [may [break {player: opp, count: 1}]]}
- dm22rp2x-026: subject を {owner: you, filter} にし、
  choose {select: {ref: event.subject}, as: dead} で束縛して
  delayed_trigger {when: turn_end} の effect が
  move {select: {ref: dead}, to: bz, reason: summon} で戻す。

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

TRIGGER_070 = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy", "battle": True, "subject": "self"},
    "effect": [{"op": "may", "body": [
        {"op": "break", "player": "opp", "count": 1}]}]}

FORM_070 = [TRIGGER_070]

CIVIL_LIGHT = {
    "kind": "static",
    "affects": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}},
    "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                              "filter": {"civs": ["light"],
                                         "types": ["creature", "tamaseed"]}}},
                   ">=", 3]},
    "mod": {"grant": ["blocker"]}}

CIVIL_DARK = {
    "kind": "static",
    "affects": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}},
    "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                              "filter": {"civs": ["darkness"],
                                         "types": ["creature", "tamaseed"]}}},
                   ">=", 3]},
    "mod": {"grant": ["slayer"]}}

RETURN_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy", "battle": True,
             "subject": {"owner": "you",
                         "filter": {"types": ["creature"]}}},
    "effect": [
        {"op": "choose", "select": {"ref": "event.subject"},
         "as": "dead"},
        {"op": "delayed_trigger", "when": {"event": "turn_end"},
         "effect": [{"op": "move", "select": {"ref": "dead"},
                     "to": "bz", "reason": "summon"}]}]}

FORM_026 = [CIVIL_LIGHT, CIVIL_DARK, RETURN_TRIGGER]


def _partial(cid):
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            if r["id"] == cid:
                return r.get("partial")
    return None


def test_targets_still_in_rejects():
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    for t in ("dm24rp4-070", "dm22rp2x-026"):
        assert t not in ids
        assert _partial(t) is not None, t


def test_partial_forms():
    p = _partial("dm24rp4-070")
    assert p["name"] == "ライラ・理・アイニー"
    assert not p.get("abilities")
    # dm22rp2x-026 の partial はシビルカウント2件が完成している
    p = _partial("dm22rp2x-026")
    assert p["abilities"] == FORM_026[:2]


def test_proto_forms_match():
    c = proto_card("T1008")
    assert c["abilities"] == FORM_070
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = proto_card("T1009")
    assert c["abilities"] == FORM_026
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
