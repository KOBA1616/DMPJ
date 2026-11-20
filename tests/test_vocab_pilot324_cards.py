"""語彙パイロット第324弾の対象カード検証（提出前）。

breaks_equal_creature_count は dm24ex2-024 / dm26ex4-cho021
（同名カード ジョジョジョ・マキシマムの2印刷）の純粋2件のみ
（multi-gap 行にも現れない）。dm24ex2-024 の partial は骨格あり
（unsupported は breaks_equal_creature_count だけ）。
dm26ex4-cho021 は partial 空。by_product で原文照合済み。

第324弾の結論はエンジン拡張（スキーマのみ）。3つの既存の形の組み合わせ
だが、breaks_add の辞書形に {var: 名前} を許可するスキーマ拡張
（dmsim/cards/defs.py Checker.mod）が必要だった。実行時は op_modify
の _bake_refs が生成時に数値へ焼くため core.py の変更は不要。
{amount, count} 形（第170弾）は攻撃時に数え直すため使えない
（解決時の数を固定するため）。
- G・ゼロ: free_if {cmp: [{count: {zone: [bz, mana], owner: you,
  filter: {race_has: ジョーカーズ}}}, '>=', 11]}
- 数えて付与: [set_var n {count: {zone: bz, owner: you,
  filter: {types: [creature]}}}; choose {zone: bz, owner: you,
  filter: {types: [creature]}, count: 1} as chosen;
  modify {ref: chosen} {breaks_add: {var: n}} end_of_turn]
- 攻撃中の呪文封じ: delayed_trigger {event: attack,
  subject: {ref: chosen}} → [modify {zone: hand, owner: opp,
  filter: {types: [spell]}} {deny: [cast]} during_attack]
  duration end_of_turn, once: false

ラウンド359で登録する。両カードとも無色・コスト9・マナ1の呪文。
dm24ex2-024 の G・ゼロ文言は「バトルゾーンまたはマナゾーンに
自分のジョーカーズが合計11枚以上あれば」、dm26ex4-cho021 は
「自分の、ジョーカーズとマナゾーンにあるジョーカーズ・カードが
合計11以上なら」（by_product の原文のまま。効果は同一）。
両 id とも real.yaml / real_akashic.yaml / real_vocab.yaml /
real_zone.yaml / proto.yaml / converted.yaml のいずれにも無く、
対象 id 自体に aliases 記録も無いことを提出前に確認済み
（dm24ex2-024 の partial には aliases [dmex19-002, dmrp04m-001]
が付いている。同名再録として submit 時に記録される見込み）。

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

TARGETS = ("dm24ex2-024", "dm26ex4-cho021")
GAP = "breaks_equal_creature_count"

FREE_IF = {
    "cmp": [{"count": {"zone": ["bz", "mana"], "owner": "you",
                       "filter": {"race_has": "ジョーカーズ"}}},
            ">=", 11]}

SPELL = [
    {"op": "set_var", "name": "n",
     "value": {"count": {"zone": "bz", "owner": "you",
                         "filter": {"types": ["creature"]}}}},
    {"op": "choose",
     "select": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}, "count": 1},
     "as": "chosen"},
    {"op": "modify", "select": {"ref": "chosen"},
     "mod": {"breaks_add": {"var": "n"}}, "duration": "end_of_turn"},
    {"op": "delayed_trigger",
     "when": {"event": "attack", "subject": {"ref": "chosen"}},
     "effect": [{"op": "modify",
                 "select": {"zone": "hand", "owner": "opp",
                            "filter": {"types": ["spell"]}},
                 "mod": {"deny": ["cast"]},
                 "duration": "during_attack"}],
     "duration": "end_of_turn", "once": False},
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
    assert len(rows) == 2047
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10270
    assert not (ids & set(rows))          # canonical 重なり0
    for tid in TARGETS:
        # 漏れ0の前提: 正本は未登録で reject 行に残っている
        assert tid not in ids and tid in rows, tid
        assert (rows[tid].get("gaps") or []) == [GAP], tid
    # breaks_equal_creature_count はこの2件だけ（multi-gap 行にも現れない）
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(TARGETS), left


def test_proto_forms_match():
    for cid in ("T990", "T991"):
        card = proto_card(cid)
        assert card["free_if"] == FREE_IF, cid
        assert card["spell"] == SPELL, cid
        d = parse_card(card, TABLES)
        assert d.free_if is not None
        assert len(d.spell) == 4
