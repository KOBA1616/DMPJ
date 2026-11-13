"""語彙パイロット第199弾のカード適用テスト（登録形）。

ラウンド235で chosen_trigger 単独9件を全件新規登録した（多重ギャップ側
にも chosen_trigger は残っていない）。dmrp20-067 は「選ばせる側」の
常在型 must_be_chosen、その他8件は {event: choose} 誘発を持つ。
"""
import copy
import json
from pathlib import Path

from dmsim.cards import cardstore
from dmsim.cards.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dm26rp3-t005", "dmr14-v02", "dmrp10-027", "dmrp18-a06",
              "dmrp20-067", "dmx12a-015", "dmx14-026", "dmx17-008",
              "dm26rp1-s007")


def _converted(cid):
    for c in cardstore.read(CONVERTED):
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        if cid == "dmrp20-067":
            assert any(a.get("mod", {}).get("must_be_chosen")
                       for a in card["abilities"]), cid
        else:
            assert any(a.get("kind") == "trigger"
                       and a.get("when", {}).get("event") == "choose"
                       for a in card["abilities"]), cid


def test_family_cleared():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    assert not [r for r in rows if "chosen_trigger" in (r.get("gaps") or [])]
