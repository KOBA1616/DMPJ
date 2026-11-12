"""語彙パイロット第198弾のカード適用テスト（登録形）。

ラウンド234で ggg_condition 単独9件を全件新規登録し、ファミリーは
全解消した。全件、G・G・G の形（手札1枚以下の if を持つ static、
または free_if）が登録形に含まれる。
"""
import copy
import json
from pathlib import Path

from dmsim import cardstore
from dmsim.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dm24ex4-026", "dm26ex1-sp004", "dm24ex4-040", "dm26rp3-s005",
              "dm26rp3-sec006", "dm26sd1-v003", "dm26sd1-v005",
              "dm24ex3-rp1tr05", "dm25ex3-rp4tr6")


def _converted(cid):
    for c in cardstore.read(CONVERTED):
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def _has_ggg_form(card):
    if card.get("free_if"):
        return True
    for ab in card.get("abilities") or []:
        cond = ab.get("if") or {}
        if "hand" in json.dumps(cond) and ab.get("kind") == "static":
            return True
    return False


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        assert _has_ggg_form(card), cid


def test_family_cleared():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    assert not [r for r in rows if "ggg_condition" in (r.get("gaps") or [])]
