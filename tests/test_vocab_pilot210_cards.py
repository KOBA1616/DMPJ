"""語彙パイロット第210弾のカード適用テスト（登録形＋差し戻し状態）。

ラウンド246: number_choice 単独8件のうち7件を新規登録し、1件を
attack_end_trigger で差し戻した（多重ギャップの行に number_choice
が1件だけ残る）。
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

REGISTERED = ("dm26ex1-n006", "dm26ex4-cho023", "dm26rp2-sp003",
              "dm26rp2-tr008", "promoy13-011", "dmrp17-015", "dm24rp1-015")
BOUNCED = {"dmrp21-002": "attack_end_trigger"}


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
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


def test_number_forms_present():
    for cid in ("dm26rp2-tr008", "promoy13-011", "dmrp17-015", "dm24rp1-015"):
        flat = json.dumps(_converted(cid).get("abilities"),
                          ensure_ascii=False)
        assert "choose_number" in flat, cid
    for cid in ("dm26ex4-cho023", "dm26rp2-sp003"):
        card = _converted(cid)
        face = card["faces"][0] if card.get("faces") else card
        assert "choose_number" in json.dumps(face.get("spell"),
                                             ensure_ascii=False), cid


def test_bounce_states():
    for cid, gap in BOUNCED.items():
        row = _reject(cid)
        assert row["gaps"] == [gap], (cid, row["gaps"])


def test_singles_cleared():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    assert not [r for r in rows if r.get("gaps") == ["number_choice"]]
