"""語彙パイロット第326弾の対象カード検証（提出前）。

blocked_break は dm39-035 / dmc34-030 の純粋2件のみ
（multi-gap 行にも現れない）。両行とも partial あり
（unsupported の断片だけ）。by_product で原文照合済み。

第326弾の結論はドリフト（追加語彙なし）。核は block イベントの
確立形（converted.yaml に129件の先例）:
- 形A（dm39-035）: 呪文が3つの継続的効果を作る。
  (1) modify {zone: bz, owner: you, filter: {types: [creature]},
  count: all} {power: 4000, breaks_add: 1} end_of_turn
  (2) delayed_trigger {event: block,
  attacker: {owner: you, filter: {types: [creature]}}}
  → [{op: break, player: opp, count: 1}] end_of_turn, once: false
  (3) modify {zone: bz, owner: you, filter: {types: [creature]},
  count: all} {deny: [{action: be_chosen, other: {types: [spell]}}]}
  end_of_turn
- 形B（dmc34-030）: 呪文が1つの継続的効果を作る。
  modify {zone: bz, owner: you, filter: {types: [creature]},
  count: all} {power: 4000, gain: [{kind: trigger,
  when: {event: block, attacker: self},
  effect: [{op: break, player: opp, count: 1}]}]} end_of_turn

注意: attack_end {blocked: true} ではない。ブロックが宣言されると
攻撃先はブロッカーの参照に書き換わるため、attack_end レコードの
target はブロッカー参照になり、target: player はブロックされた
攻撃に決して一致しない（実測で確認）。op_modify の select は
count の既定が1なので「自分のクリーチャーすべて」には
count: all が要る。

ラウンド361で登録する。両 id とも real.yaml / real_akashic.yaml /
real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml の
いずれにも無く、対象 id 自体に aliases 記録も無いことを提出前に
確認済み（dmc34-030 の aliases [dm13-025] は submit 時に自動記録）。

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

TARGETS = ("dm39-035", "dmc34-030")
GAP = "blocked_break"

TRIGGER = {"kind": "trigger",
           "when": {"event": "block", "attacker": "self"},
           "effect": [{"op": "break", "player": "opp", "count": 1}]}

FORM_A = [
    {"op": "modify",
     "select": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}, "count": "all"},
     "mod": {"power": 4000, "breaks_add": 1},
     "duration": "end_of_turn"},
    {"op": "delayed_trigger",
     "when": {"event": "block",
              "attacker": {"owner": "you",
                           "filter": {"types": ["creature"]}}},
     "effect": [{"op": "break", "player": "opp", "count": 1}],
     "duration": "end_of_turn", "once": False},
    {"op": "modify",
     "select": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}, "count": "all"},
     "mod": {"deny": [{"action": "be_chosen",
                       "other": {"types": ["spell"]}}]},
     "duration": "end_of_turn"},
]

FORM_B = [
    {"op": "modify",
     "select": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}, "count": "all"},
     "mod": {"power": 4000, "gain": [TRIGGER]},
     "duration": "end_of_turn"},
]


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_not_yet_registered():
    rows = _rows()
    assert len(rows) == 2043
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10273
    assert not (ids & set(rows))          # canonical 重なり0
    for tid in TARGETS:
        # 漏れ0の前提: 正本は未登録で reject 行に残っている
        assert tid not in ids and tid in rows, tid
        assert (rows[tid].get("gaps") or []) == [GAP], tid
    # blocked_break はこの2件だけ（multi-gap 行にも現れない）
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(TARGETS), left


def test_proto_forms_match():
    c994 = proto_card("T994")
    assert c994["spell"] == FORM_A
    d = parse_card(c994, TABLES)
    assert len(d.spell) == 3
    c995 = proto_card("T995")
    assert c995["spell"] == FORM_B
    d = parse_card(c995, TABLES)
    assert len(d.spell) == 1
