"""語彙パイロット第203弾のカード適用テスト（登録形＋差し戻し状態）。

ラウンド239: unblocked_trigger 単独8件のうち7件を新規登録し、1件を
差し戻した。dmex10-041 の partial にはプレイヤー攻撃の形が残り、
ギャップは unblocked_creature_attack に精緻化されている。
"""
import copy
import json
from pathlib import Path

from dmsim import cardstore
from dmsim.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dmex08-068", "dmr03-007", "dmr09-007", "dmrp09-s02",
              "dmx26-005", "promoy2-023", "promoy6-022")


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
        assert "delayed_trigger" in flat, cid


def test_bounce_state():
    r = _reject("dmex10-041")
    assert r.get("gaps") == ["unblocked_creature_attack"]
    flat = json.dumps(r["partial"].get("abilities"), ensure_ascii=False)
    assert "delayed_trigger" in flat
