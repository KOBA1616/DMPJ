"""語彙パイロット第323弾の対象カード検証（提出前）。

unblocked_condition は dmx04-011 ケロディ二郎 / dmx09-049 誕生の祈
の純粋2件のみ（multi-gap 行にも現れない）。両行とも partial は空で、
unsupported に unblocked_condition だけが残る。by_product
（x04.jsonl / x09.jsonl）で原文照合済み。両カードとも単一能力の
クリーチャーで、全文が「このクリーチャーが相手プレイヤーを攻撃して
ブロックされなかった時」の1節だけ。

第323弾の結論はドリフト（追加語彙なし）。第321弾で確立した
attack_end {subject: self, target: player, blocked: false} そのもの。
- 形A（dmx04-011）: trigger {event: attack_end, subject: self,
  target: player, blocked: false} → may [move {zone: bz, owner: any,
  filter: {types: [creature]}, count: 1} to hand, reason: return]
- 形B（dmx09-049）: 同じ when → may [choose {zone: deck, owner: you,
  look: true, filter: {types: [creature]}, count: 1} as t;
  move {ref: t, count: all} to hand, reason: draw; shuffle]

ラウンド358で登録する。dmx04-011 は水・コスト4・パワー2000・
ゲル・フィッシュ/ハンター・マナ1、dmx09-049 は自然・コスト3・
パワー2000・ビーストフォーク・マナ1。両 id とも real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml /
converted.yaml のいずれにも無く、aliases 記録も無いことを提出前に
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

TARGETS = ("dmx04-011", "dmx09-049")
GAP = "unblocked_condition"

FORM_A = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "may", "body": [
        {"op": "move",
         "select": {"zone": "bz", "owner": "any", "filter": {"types": ["creature"]},
                    "count": 1},
         "to": "hand", "reason": "return"}]}]}
FORM_B = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "may", "body": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "look": True,
                    "filter": {"types": ["creature"]}, "count": 1},
         "as": "t"},
        {"op": "move", "select": {"ref": "t", "count": "all"},
         "to": "hand", "reason": "draw"},
        {"op": "shuffle"}]}]}


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_not_yet_registered():
    rows = _rows()
    assert len(rows) == 2049
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10268
    assert not (ids & set(rows))          # canonical 重なり0
    for tid in TARGETS:
        # 漏れ0の前提: 正本は未登録で reject 行に残っている
        assert tid not in ids and tid in rows, tid
        assert (rows[tid].get("gaps") or []) == [GAP], tid
        assert not (rows[tid].get("partial") or {}).get("abilities"), tid
    # unblocked_condition はこの2件だけ（multi-gap 行にも現れない）
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(TARGETS), left


def test_proto_forms_match_established():
    proto = parse_card(proto_card("T988"), TABLES)
    assert FORM_A in proto.abilities
    proto989 = parse_card(proto_card("T989"), TABLES)
    assert FORM_B in proto989.abilities
    # 第321弾の確立形（T984）と when が同一であること（生の proto 辞書で
    # 比べる。parse 後の T984 は abilities[0] がダイナモの activate になる）
    when984 = proto_card("T984")["abilities"][0]["when"]
    assert proto_card("T988")["abilities"][0]["when"] == when984
    assert proto_card("T989")["abilities"][0]["when"] == when984
