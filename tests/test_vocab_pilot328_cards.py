"""語彙パイロット第328弾の対象カード検証（提出前）。

dmex15-b019 滅亡の光は multi-gap 2件（filter_not_race＋
first_attack_end）の1行だけ。partial あり（アタック・チャンスは
declare＋play_free で変換済み）。by_product で原文照合済み。
canon_id は dmex15-b019 で aliases 無し。

第328弾の結論はドリフト（追加語彙なし）:
- filter_not_race: [destroy {zone: bz, owner: any,
  filter: {types: [creature],
  not_race_has: [ゴッド, フェニックス, クリエイター]}, count: all}]
- first_attack_end 各クリーチャー: [modify {zone: bz, owner: any,
  filter: {any_of: [{race_has: ゴッド}, {race_has: フェニックス},
  {race_has: クリエイター}]}, count: all},
  mod: {gain: [{kind: trigger,
  when: {event: attack_end, subject: self},
  effect: [{op: untap, select: {ref: self}}], once_per_turn: true}]},
  duration: end_of_turn]
（アタック・チャンスは partial どおり declare＋play_free）

ラウンド363で登録する。正本は real.yaml / real_akashic.yaml /
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

TARGET = "dmex15-b019"

DECLARE = {"kind": "declare", "zone": "hand",
           "when": {"event": "attack",
                    "subject": {"owner": "you",
                                "filter": {"race_has": "クリエイター"}}},
           "effect": [{"op": "play_free", "select": {"ref": "self"}}]}

TRIGGER = {"kind": "trigger",
           "when": {"event": "attack_end", "subject": "self"},
           "effect": [{"op": "untap", "select": {"ref": "self"}}],
           "once_per_turn": True}

FORM = [
    {"op": "destroy",
     "select": {"zone": "bz", "owner": "any",
                "filter": {"types": ["creature"],
                           "not_race_has": ["ゴッド", "フェニックス",
                                            "クリエイター"]},
                "count": "all"}},
    {"op": "modify",
     "select": {"zone": "bz", "owner": "any",
                "filter": {"any_of": [{"race_has": "ゴッド"},
                                      {"race_has": "フェニックス"},
                                      {"race_has": "クリエイター"}]},
                "count": "all"},
     "mod": {"gain": [TRIGGER]},
     "duration": "end_of_turn"},
]


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_target_not_yet_registered():
    rows = _rows()
    assert len(rows) == 2039
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10276
    assert not (ids & set(rows))          # canonical 重なり0
    # 漏れ0の前提: 正本は未登録で reject 行に残っている
    assert TARGET not in ids and TARGET in rows
    assert rows[TARGET].get("gaps") == ["filter_not_race",
                                        "first_attack_end"]
    # この2つの gap を持つ行は dmex15-b019 だけ
    left = {rid for rid, r in rows.items()
            if "filter_not_race" in (r.get("gaps") or [])
            or "first_attack_end" in (r.get("gaps") or [])}
    assert left == {TARGET}, left


def test_proto_forms_match():
    c997 = proto_card("T997")
    assert c997["abilities"] == [DECLARE]
    assert c997["spell"] == FORM
    d = parse_card(c997, TABLES)
    assert len(d.spell) == 2
