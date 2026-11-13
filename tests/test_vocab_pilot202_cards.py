"""語彙パイロット第202弾のカード適用テスト（登録形）。

ラウンド238で trigger_when_opponent_uses_s_trigger 単独8件を全件
新規登録し、ファミリーは全解消した。7件は use_s_trigger 誘発を持ち、
dmbd22-017 は「S・トリガーを持つカードを使った時」を cast/召喚への
subject フィルタ誘発で受ける（use_s_trigger 誘発は持たない）。
"""
import copy
import json
from pathlib import Path

from dmsim.cards import cardstore
from dmsim.cards.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dm08-s02", "dm09-001", "dm20-s01", "dm23-010", "dm23-014",
              "dm23-020", "dmbd22-017", "dm12-053")


def _converted(cid):
    for c in cardstore.read(CONVERTED):
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        if cid == "dmbd22-017":
            assert any(a.get("when", {}).get("event") == "cast"
                       for a in card["abilities"]), cid
            assert any(a.get("zone") == "graveyard"
                       for a in card["abilities"]), cid
        else:
            assert any(a.get("when", {}).get("event") == "use_s_trigger"
                       for a in card["abilities"]), cid


def test_family_cleared():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    assert not [r for r in rows
                if "trigger_when_opponent_uses_s_trigger" in (r.get("gaps") or [])]
