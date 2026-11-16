"""第214弾の登録カード（ラウンド250）の確認。

- 5枚が converted.yaml の登録形で parse できる
- dm24ex4-022: 相手の大物がいるターン終わりに手札から無料召喚される
- dmx12b-092: 相手が山札からシールドを加えたターン終わりに無料召喚される
- dm38-014: 出た時、相手が自身のクリーチャーを選んでマナゾーンに置く
"""
import os
from pathlib import Path

import pytest

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.scenario import build  # noqa: E402
import tests._conv_cache as _conv_cache  # noqa: E402

TABLES = load_tables()
CONVERTED = Path(__file__).parent.parent / "data" / "cards" / "converted.yaml"
IDS = ("dm24ex4-022", "dm38-014", "dmx12b-092", "dmx18-020", "dmx19-s44")


@pytest.fixture(scope="module")
def converted():
    return {c["id"]: c for c in _conv_cache.all_cards(str(CONVERTED))}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_build_forms_parse(converted):
    for cid in IDS:
        assert cid in converted, cid
        parse_card(converted[cid], TABLES)


def _in_bz(e, defn, ctrl):
    return any(e.s.cards[c].defn == defn and e.s.cards[c].controller == ctrl
               for c in e.zlist("bz", 0))


def _run(e, plays, stop, limit=800):
    plays = {p: list(v) for p, v in plays.items()}
    for _ in range(limit):
        if stop():
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        p = d.get("player")
        if d["kind"] == "yes_no":
            e.answer([0])
        elif d["kind"] in ("main", "attack"):
            todo = plays.get(p) or []
            hit = next((k for k in todo if k in keys), None)
            if hit is not None:
                todo.remove(hit)
                e.answer([keys.index(hit)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def test_world_is_mine_revenge_chance(rules):
    e = build(rules, {"p0": {"hand": ["dm24ex4-022"]}, "p1": {"bz": ["T201"]},
                      "filler": "T002", "seed": 1, "deck_size": 20})
    _run(e, {}, stop=lambda: _in_bz(e, "dm24ex4-022", 0) or e.s.turn >= 3)
    assert _in_bz(e, "dm24ex4-022", 0)


def test_cupricorn_revenge_chance_on_deck_shield(rules):
    e = build(rules, {"p0": {"hand": ["dmx12b-092"]},
                      "p1": {"hand": ["T549"], "mana": ["T030", "T030"]},
                      "filler": "T002", "seed": 1, "deck_size": 20})
    _run(e, {1: ["play:T549"]},
         stop=lambda: _in_bz(e, "dmx12b-092", 0) or e.s.turn >= 3)
    assert _in_bz(e, "dmx12b-092", 0)


def test_kumatta_cip_opponent_puts_own_creature_to_mana(rules):
    e = build(rules, {"p0": {"hand": ["dm38-014"], "mana": ["T002"] * 7},
                      "p1": {"bz": ["T002"]},
                      "filler": "T002", "seed": 1, "deck_size": 20})
    def settled():
        return _in_bz(e, "dm38-014", 0) and \
            any(e.s.cards[c].defn == "T002" for c in e.zlist("mana", 1))
    _run(e, {0: ["play:dm38-014"]}, stop=lambda: settled() or e.s.turn >= 3)
    assert settled()
