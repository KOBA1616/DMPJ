"""語彙パイロット第208弾のカード適用テスト（登録形）。

ラウンド244: j_crime 単独8件を全件新規登録し、ファミリーは全解消
した。全カードが op swap の入れ替え能力を持つ。
"""
import copy
import json
from pathlib import Path

from dmsim import cardstore
from dmsim.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dm26rp3-016", "dm26rp3-037", "dm26rp3-062", "dm26rp3-064",
              "dm26rp3-065", "dm26rp3-s004", "dm26rp3-sec005", "dm26rp3-sec023")


def _converted(cid):
    for c in cardstore.read(CONVERTED):
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        flat = json.dumps(card.get("abilities"), ensure_ascii=False)
        assert '"swap"' in flat, cid


def test_family_cleared():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    assert not [r for r in rows if "j_crime" in (r.get("gaps") or [])]
