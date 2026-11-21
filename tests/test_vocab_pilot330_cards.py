"""語彙パイロット第330弾の対象カード検証（提出前）。

対象は pure な destroyed_while_tapped 2件（いずれも partial あり）:
- dm26ex1-021 勝利龍装 クラッシュ"覇道"（partial は B・A・D の
  static のみ。canon_id は自身、登録時に aliases 7件が自動記録
  される見込み）
- dmr18-s04 超復讐 ギャロウィン（partial は侵略の declare と
  「自分の他のクリーチャーが破壊された時」の誘発まで変換済み。
  不足は自身が破壊された場合だけ。canon_id は自身、aliases 無し）

第330弾の結論はエンジン拡張（条件キー subject_tapped の追加）:
{subject_tapped: bool} は env["event"]["lki"]["tapped"]（移動
直前のタップ状態）を読む。defs.py Checker.cond＋schema.py＋
card.schema.json 再生成＋selectors.py eval_cond の4点セット。
他の条項は既存形（extra_turn op／battle_power mod／exists の
タップ条件）。

ラウンド365で登録する。正本は real.yaml / real_akashic.yaml /
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

TARGETS = {"dm26ex1-021", "dmr18-s04"}

BAD = {"kind": "static", "affects": "self", "zone": "hand",
       "mod": {"opt_reduce": {"amount": 2, "then": "destroy"}}}

DESTROYED_TAPPED = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy", "subject": "self"},
    "if": {"subject_tapped": True},
    "effect": [{"op": "extra_turn"}]}

BATTLE_POWER = {"kind": "static", "affects": "self",
                "mod": {"battle_power": {"amount": 5000}}}

FORM_021 = [BAD, DESTROYED_TAPPED, BATTLE_POWER]

DECLARE = {"kind": "declare", "zone": "hand",
           "when": {"event": "attack",
                    "subject": {"owner": "you",
                                "filter": {"civs": ["darkness"],
                                           "race_has": "コマンド"}}},
           "effect": [{"op": "may",
                       "body": [{"op": "invade",
                                 "onto": {"ref": "event.subject"}}]}]}

EFFECT_S04 = [
    {"op": "destroy",
     "select": {"zone": "bz", "owner": "opp",
                "filter": {"types": ["creature"]}, "count": 1}},
    {"op": "move",
     "select": {"zone": "graveyard", "owner": "you",
                "filter": {"civs": ["darkness"],
                           "types": ["creature"],
                           "not_name": "超復讐 ギャロウィン"},
                "count": 1},
     "to": "hand", "reason": "return"}]

OTHER_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy",
             "subject": {"owner": "you", "other": True,
                         "filter": {"types": ["creature"]}}},
    "if": {"exists": {"ref": "self", "filter": {"tapped": True}}},
    "effect": EFFECT_S04}

SELF_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy", "subject": "self"},
    "if": {"subject_tapped": True},
    "effect": EFFECT_S04}

FORM_S04 = [DECLARE, OTHER_TRIGGER, SELF_TRIGGER]


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_not_yet_registered():
    rows = _rows()
    assert len(rows) == 2036
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10279
    assert not (ids & set(rows))          # canonical 重なり0
    # 漏れ0の前提: 正本は未登録で reject 行に残っている
    assert not (TARGETS & ids) and TARGETS <= set(rows)
    for t in TARGETS:
        assert rows[t].get("gaps") == ["destroyed_while_tapped"]
    left = {rid for rid, r in rows.items()
            if "destroyed_while_tapped" in (r.get("gaps") or [])}
    assert left == TARGETS, left


def test_proto_forms_match():
    c = proto_card("T1001")
    assert c["abilities"] == FORM_021
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
    c = proto_card("T1002")
    # proto 側は not_name が proto 名（試験用ギャロウィン）になる
    assert c["abilities"][0] == DECLARE
    assert c["abilities"][1]["when"] == OTHER_TRIGGER["when"]
    assert c["abilities"][1]["if"] == OTHER_TRIGGER["if"]
    assert c["abilities"][2]["when"] == SELF_TRIGGER["when"]
    assert c["abilities"][2]["if"] == SELF_TRIGGER["if"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
