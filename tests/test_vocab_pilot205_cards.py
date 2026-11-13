"""語彙パイロット第205弾のカード適用テスト（登録形＋差し戻し状態）。

ラウンド241: labyrinth 単独8件のうち6件を新規登録し、2件を差し戻して
labyrinth は全解消した。差し戻し2件の partial には解ける条項が残り、
ギャップは shield_hand_strigger_use / labyrinth_trigger_redirect に
精緻化されている。
"""
import copy
import json
from pathlib import Path

from dmsim.cards import cardstore
from dmsim.cards.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dm22bd2-010", "dmrp01-s02", "dmrp02-014", "dmrp03-063",
              "dmsd02-001", "dmsd02-006")
BOUNCED = {"dmbd04-001": "shield_hand_strigger_use",
           "dmrp03-003": "labyrinth_trigger_redirect"}


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


def test_bounce_state():
    for cid, gap in BOUNCED.items():
        r = _reject(cid)
        assert r.get("gaps") == [gap], cid
        assert r["partial"].get("abilities"), cid


def test_family_cleared():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    assert not [r for r in rows if "labyrinth" in (r.get("gaps") or [])]
