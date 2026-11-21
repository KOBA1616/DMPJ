"""語彙パイロット第327弾の対象カード検証（提出前）。

first_attack_end は dm26ex4-cho025 / dm26sd1-i004 の純粋2件のみ
（multi-gap 行にも現れない）。同一カード瞬閃と疾駆と双撃の決断の
2印刷で、canon_id は dm26ex4-cho025。両行とも partial あり
（unsupported の断片だけ）。by_product で原文照合済み（正本は
cho025 の文面。sd1-i004 の文面はモード2に注釈が付くが、注釈は
データモデルに無いため正本の文面で登録する）。

第327弾の結論はドリフト（追加語彙なし）。modal op が「次の中から
２回選ぶ（同じものを選んでもよい）」をそのまま表す（count: 2,
repeat: true。12件の repeat-modal の先例）。モード3の
first_attack_end は once 既定の遅延誘発:
[choose {zone: bz, owner: you, filter: {types: [creature]},
count: 1} as: chosen,
delayed_trigger {event: attack_end, subject: {ref: chosen}}
→ [{op: untap, select: {ref: chosen}}] end_of_turn]。

ラウンド362で登録する。正本 dm26ex4-cho025 は real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml /
converted.yaml のいずれにも無く、対象 id 自体に aliases 記録も無い
ことを提出前に確認済み（dm26sd1-i004 は submit 時に aliases へ
自動記録）。

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

TARGETS = ("dm26ex4-cho025", "dm26sd1-i004")
GAP = "first_attack_end"

FORM = [
    {"op": "modal", "count": 2, "repeat": True,
     "modes": [
         [{"op": "play_free",
           "select": {"zone": "hand", "owner": "you",
                      "filter": {"types": ["creature"], "cost_le": 3},
                      "count": 1}}],
         [{"op": "choose",
           "select": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["creature"]}, "count": 1},
           "as": "c"},
          {"op": "modify", "select": {"ref": "c", "count": "all"},
           "mod": {"grant": ["speed_attacker"]},
           "duration": "end_of_turn"}],
         [{"op": "choose",
           "select": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["creature"]}, "count": 1},
           "as": "chosen"},
          {"op": "delayed_trigger",
           "when": {"event": "attack_end", "subject": {"ref": "chosen"}},
           "effect": [{"op": "untap", "select": {"ref": "chosen"}}],
           "duration": "end_of_turn"}],
     ]},
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
    assert len(rows) == 2041
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10275
    assert not (ids & set(rows))          # canonical 重なり0
    for tid in TARGETS:
        # 漏れ0の前提: 正本は未登録で reject 行に残っている
        assert tid not in ids and tid in rows, tid
        assert (rows[tid].get("gaps") or []) == [GAP], tid
    # first_attack_end は純粋2件＋multi-gap 1件（dmex15-b019 滅亡の光。
    # 「それぞれの最初の攻撃」は once_per_turn の付与型で書く見込みで、
    # filter_not_race と合わせて第328弾の候補。今回は対象外）
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(TARGETS) | {"dmex15-b019"}, left
    assert rows["dmex15-b019"].get("gaps") == ["filter_not_race",
                                               "first_attack_end"]


def test_proto_forms_match():
    c996 = proto_card("T996")
    assert c996["spell"] == FORM
    d = parse_card(c996, TABLES)
    assert len(d.spell) == 1 and d.spell[0]["op"] == "modal"
