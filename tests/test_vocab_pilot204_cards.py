"""語彙パイロット第204弾のカード適用テスト（登録形＋差し戻し状態）。

ラウンド240: henrei 単独9件のうち8件を新規登録し、1件を差し戻して
henrei は全解消した。dm36-005 の partial には攻撃時の返霊の形が残り、
ギャップは jigoku_henrei に精緻化されている。
"""
import copy
import json
from pathlib import Path

from dmsim import cardstore
from dmsim.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dm36-006", "dm36-024", "dm36-055", "dm36-088", "dm36-090",
              "dm38-002", "dm38-044", "dm38-047")


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
        flat = json.dumps(card.get("abilities"), ensure_ascii=False)
        assert '"paid"' in flat, cid


def test_bounce_state():
    r = _reject("dm36-005")
    assert r.get("gaps") == ["jigoku_henrei"]
    flat = json.dumps(r["partial"].get("abilities"), ensure_ascii=False)
    assert '"paid"' in flat


def test_family_cleared():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    assert not [r for r in rows if "henrei" in (r.get("gaps") or [])]
