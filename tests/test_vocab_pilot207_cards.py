"""語彙パイロット第207弾のカード適用テスト（登録形）。

ラウンド243: deck_limit_exception 単独8件を全件新規登録した
（多重ギャップの行に1件だけ残る）。デッキ構築の文は defs に
表されていない。
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

REGISTERED = ("dmr12-029", "dmr16g-043", "dmr16g-046", "dmr16g-051",
              "dmr16s-035", "dmr16s-040", "dmr21-059", "dmrp04s-082")


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)


def test_singles_cleared():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    assert not [r for r in rows
                if r.get("gaps") == ["deck_limit_exception"]]
