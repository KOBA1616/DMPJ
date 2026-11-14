"""語彙パイロット第195弾のカード適用テスト（登録形）。

ラウンド231で cross_free_permission 単独9件＋cross_free_op 単独5件、
計14件を新規登録した。
- permission 側: 登録形に allow [cross_free] の static が含まれること。
  発生源は4形（クリーチャー自身／ギア自身＋other／ギアから宿主へ
  affects: crossed／全体付与 affects ギア全体）。
- op 側: 登録形に op cross_free が含まれること。
- 残件: cross_free_permission は多重ギャップ1件、cross_free_op は
  多重ギャップ9件のみ（単独は全解消）。
"""
import copy
import json
from pathlib import Path

from dmsim.cards import cardstore

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

PERMISSION = ("dmex03-018", "dm23ex1-050", "dm26sd1-r003", "dm26sd1-r006",
              "dm35-020", "dmc56-004", "dmc67-008", "dmex15-a030", "dmex17-051")
OP = ("dmex16-043", "dmc42-010", "dmc59-002", "dmex16-042", "dm15-025")


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject_rows():
    return [json.loads(l) for l in open(REJECTS, encoding="utf-8")]


def _walk(x, key, val, out):
    if isinstance(x, dict):
        if x.get(key) == val:
            out.append(x)
        for v in x.values():
            _walk(v, key, val, out)
    elif isinstance(x, list):
        for v in x:
            _walk(v, key, val, out)


def test_permission_forms():
    for cid in PERMISSION:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        hits = []
        _walk(card.get("abilities") or [], "action", "cross_free", hits)
        assert hits, cid


def test_op_forms():
    for cid in OP:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        hits = []
        _walk(card.get("abilities") or [], "op", "cross_free", hits)
        assert hits, cid


def test_family_leftovers_are_multi_gap_only():
    for gap in ("cross_free_permission", "cross_free_op"):
        left = [r for r in _reject_rows() if gap in (r.get("gaps") or [])]
        assert all(len(r.get("gaps") or []) > 1 for r in left), gap
