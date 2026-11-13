"""語彙パイロット第197弾のカード適用テスト（登録形）。

ラウンド233で10件を新規登録した:
- 単独4件（dm35-021 / dm35-037 / dm35-045 / dmc63-011）は reopen 経由。
- link_establish_event との複合6件は、reopen のプール計算が
  link_establish_event 単独と付いた別件26行（実不足は別物の付替え漏れ）
  まで巻き込むため、reopen を使わず submit で直接登録した
  （submit は id で rejects 行を落とす。実験で確認済み）。
全件 link_to を持ち、複合6件は link_established 誘発を持つ。
"""
import copy
import json
from pathlib import Path

from dmsim.cards import cardstore
from dmsim.cards.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dm35-021", "dm35-037", "dm35-045", "dmc63-011",
              "dm33-017", "dm33-035", "dm34-017", "dmc63-003",
              "dmc63-014", "dmc63-016")
COMBOS = ("dm33-017", "dm33-035", "dm34-017", "dmc63-003", "dmc63-014", "dmc63-016")


def _converted(cid):
    for c in cardstore.read(CONVERTED):
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        assert card.get("link_to"), cid
    for cid in COMBOS:
        card = _converted(cid)
        assert any(a.get("kind") == "trigger"
                   and a.get("when", {}).get("event") == "link_established"
                   for a in card["abilities"]), cid
    trig = _converted("dmc63-011")["abilities"]
    assert [t["when"]["event"] for t in trig] == ["attack", "block"]


def test_family_leftovers_are_multi_gap_only():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    left = [r for r in rows if "g_link_four_way" in (r.get("gaps") or [])]
    assert left and all(len(r.get("gaps") or []) > 1 for r in left)
