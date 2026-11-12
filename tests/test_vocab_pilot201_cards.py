"""語彙パイロット第201弾のカード適用テスト（登録形＋差し戻し状態）。

ラウンド237: sasageeru 単独7件のうち6件を新規登録し、1件を精緻化して
差し戻した（sac_reduce_followup）。
"""
import copy
import json
from pathlib import Path

from dmsim import cardstore
from dmsim.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dm26rp3-057", "dm26rp3-061", "dm26rp3-066", "dm26rp3-071",
              "dm26rp3-075", "dm26rp3-020")


def _converted(cid):
    for c in cardstore.read(CONVERTED):
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        assert any(a.get("mod", {}).get("sac_reduce") == 2
                   for a in card["abilities"]), cid


def test_bounced_state():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    r = next(x for x in rows if x["id"] == "dmrp19-054")
    assert r["gaps"] == ["sac_reduce_followup"]
    assert not [x for x in rows if "sasageeru" in (x.get("gaps") or [])]
