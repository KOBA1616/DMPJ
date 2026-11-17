"""第213弾の登録カード（ラウンド249）の確認。

- 5枚が converted.yaml の登録形で parse できる
- 冥逝邪夢（dm23rp2x-018）: 墓地のクリーチャーがタップして出て、出た時能力は誘発しない
- ブラキオ龍樹（dm26ex1-026）: 相手のクリーチャーが出た時、その能力は誘発しない
"""
import os
from pathlib import Path

import pytest
import yaml

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.scenario import build  # noqa: E402
import tests._conv_cache as _conv_cache  # noqa: E402

TABLES = load_tables()
CONVERTED = Path(__file__).parent.parent / "data" / "cards" / "converted.yaml"
IDS = ("dm23rp2x-018", "dm25ex3-rp3s09", "dm26ex1-026", "dm26ex4-cho019", "dmart26-006")


@pytest.fixture(scope="module")
def converted():
    return {c["id"]: c for c in _conv_cache.all_cards(str(CONVERTED))}


@pytest.fixture(scope="module")
def rules():
    return _conv_cache.full_rules()


def test_build_forms_parse(converted):
    for cid in IDS:
        assert cid in converted, cid
        parse_card(converted[cid], TABLES)


def _drive(e, player, key, stop, limit=500):
    acted = False
    before = None
    settled = False
    for _ in range(limit):
        if acted and stop() and settled:
            return before
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not acted and d.get("player") == player and d["kind"] in ("main", "attack") and key in keys:
            before = len(e.zlist("hand", player))
            e.answer([keys.index(key)])
            acted = True
        elif acted and stop() and d["kind"] in ("main", "charge"):
            settled = True
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return before


def test_meissei_puts_tapped_without_triggers(rules):
    e = build(rules, {"p0": {"hand": ["dm23rp2x-018"], "mana": ["T050"] * 9,
                             "graveyard": ["T537"]},
                      "p1": {}, "filler": "T002", "seed": 1, "deck_size": 20})
    def in_bz_tapped():
        return any(e.s.cards[c].defn == "T537" and e.s.cards[c].tapped
                   for c in e.zlist("bz", 0))
    before = _drive(e, 0, "play:dm23rp2x-018", in_bz_tapped)
    assert before is not None and in_bz_tapped()
    # 呪文1枚を消費し、出た T537 の CIP（ドロー）は誘発しない
    assert len(e.zlist("hand", 0)) == before - 1


def test_burakio_suppresses_opponent_cip(rules):
    e = build(rules, {"p0": {"bz": ["dm26ex1-026"]},
                      "p1": {"hand": ["T537"], "mana": ["T002", "T002", "T002"]},
                      "filler": "T002", "seed": 1, "deck_size": 20})
    def entered():
        return any(e.s.cards[c].defn == "T537" and e.s.cards[c].controller == 1
                   for c in e.zlist("bz", 0))
    before = _drive(e, 1, "play:T537", entered)
    assert before is not None and entered()
    # 召喚で1枚減っただけ（CIP のドローは抑制された）
    assert len(e.zlist("hand", 1)) == before - 1
