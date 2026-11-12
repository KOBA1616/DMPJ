"""語彙パイロット第209弾のカード適用テスト（登録形＋差し戻し状態）。

ラウンド245: alternative_summon_cost 単独8件のうち5件を新規登録し、
3件を精緻化したギャップで差し戻した。ファミリーは全解消した。
"""
import copy
import json
from pathlib import Path

from dmsim import cardstore
from dmsim.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dm22rp1-018", "dm22rp1-065", "dm22rp1-042", "dm22rp1-5a",
              "dm23rp2x-tr06")
BOUNCED = {"dm25ex3-sp1": "after_attack_destroy",
           "dmart10-002": "after_attack_destroy",
           "dm26ex4-039": "hyperdimensional_zone"}


def _converted(cid):
    for c in cardstore.read(CONVERTED):
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def _reject(cid):
    for line in open(REJECTS, encoding="utf-8"):
        r = json.loads(line)
        if r["id"] == cid:
            return r
    raise KeyError(cid)


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        assert card.get("alt_cost"), cid


def test_bounce_states():
    for cid, gap in BOUNCED.items():
        row = _reject(cid)
        assert row["gaps"] == [gap], (cid, row["gaps"])


def test_family_cleared():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    assert not [r for r in rows
                if "alternative_summon_cost" in (r.get("gaps") or [])]
