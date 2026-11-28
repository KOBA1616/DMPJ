"""語彙パイロット第330弾の対象カード検証（登録形）。

対象は pure な destroyed_while_tapped 2件（いずれも partial あり）:
- dm26ex1-021 勝利龍装 クラッシュ"覇道": rejects 行の id は
  非正本で、正本は dm26rp3-tr005（identity.canon_id）。正本は
  既に登録済みだったが、2条項が壊れていた（下記）。行は stale
  クリーンアップとして reopen で除去済み。
- dmr18-s04 超復讐 ギャロウィン: ラウンド365で新規登録。
  canon_id は自身、aliases 無し。

正本 dm26rp3-tr005 の登録形は当初、破壊時誘発が
zone: graveyard＋if exists {ref: self, filter: {tapped: true}}
（墓地に置かれたカードはアンタップに戻るため決して誘発しない）、
battle_power の常在型が affects: {ref: self}（_battle_bonus が
self と扱わず効かない）で、いずれも実挙動で不発を確認した。
ラウンド365で第330弾の形（affects: self／when move from bz
reason destroy＋if subject_tapped）に修正し、実挙動で確認済み。
登録形の能力順は [B・A・D static, battle_power static, 誘発]。

第330弾の結論はエンジン拡張（条件キー subject_tapped の追加）:
{subject_tapped: bool} は env["event"]["lki"]["tapped"]（移動
直前のタップ状態）を読む。defs.py Checker.cond＋schema.py＋
card.schema.json 再生成＋selectors.py eval_cond の4点セット。

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

FORM_021_PROTO = [BAD, DESTROYED_TAPPED, BATTLE_POWER]
FORM_021_CANON = [BAD, BATTLE_POWER, DESTROYED_TAPPED]

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


def test_targets_registered():
    rows = _rows()
    assert len(rows) <= 2034  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10280  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    # dm26ex1-021 の行は stale として除去済み（登録もされない）
    assert "dm26ex1-021" not in ids and "dm26ex1-021" not in rows
    # 正本 dm26rp3-tr005 は第330弾の形に修正された登録形
    c = _conv_cache.find(CONVERTED, "dm26rp3-tr005")
    assert c is not None
    assert c["abilities"] == FORM_021_CANON
    assert c["keywords"] == ["speed_attacker", "double_breaker"]
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
    # dmr18-s04 は新規登録
    assert "dmr18-s04" in ids and "dmr18-s04" not in rows
    c = _conv_cache.find(CONVERTED, "dmr18-s04")
    assert c is not None
    assert c["abilities"] == FORM_S04
    assert c["keywords"] == ["double_breaker"]
    assert not (c.get("source") or {}).get("unsupported")
    assert not (c.get("source") or {}).get("aliases")
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
    # destroyed_while_tapped は残り0件でファミリー解消
    left = {rid for rid, r in rows.items()
            if "destroyed_while_tapped" in (r.get("gaps") or [])}
    assert left == set(), left


def test_proto_forms_match():
    c = proto_card("T1001")
    assert c["abilities"] == FORM_021_PROTO
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
    c = proto_card("T1002")
    assert c["abilities"][0] == DECLARE
    assert c["abilities"][1]["when"] == OTHER_TRIGGER["when"]
    assert c["abilities"][1]["if"] == OTHER_TRIGGER["if"]
    assert c["abilities"][2]["when"] == SELF_TRIGGER["when"]
    assert c["abilities"][2]["if"] == SELF_TRIGGER["if"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
