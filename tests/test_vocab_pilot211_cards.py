"""語彙パイロット第211弾のカード適用テスト（登録形＋クリーンアップ状態）。

ラウンド247: battle_end_trigger 単独6件のうち3件を新規登録し、
3件は同一カードの別刷りが登録済みだったため stale クリーンアップ
とした。ファミリーは全解消した。登録済みの正規刷りは battle_win
誘発で同じ効果を表しており完全な登録だった。
"""
import copy
import json
from pathlib import Path

from dmsim import cardstore
from dmsim.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dmbd16-teki005", "dmc44-017", "dmc61-075")
STALE = {"dmc37-008": "dm05-001", "dmd02-004": "dm06-027",
         "dmd02-014": "dm01-089"}


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
        assert "battle_end" in flat, cid


def test_stale_cleanup_state():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    left = {r["id"] for r in rows}
    for cid, canonical in STALE.items():
        assert cid not in left
        _converted(canonical)   # 正規刷りが登録済み


def test_family_cleared():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    assert not [r for r in rows
                if "battle_end_trigger" in (r.get("gaps") or [])]
