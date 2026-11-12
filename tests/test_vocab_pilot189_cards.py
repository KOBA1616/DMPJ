"""語彙パイロット第189弾のカード側テスト（登録形）: ラウンド225の結果。

- 登録11件: converted.yaml にあり、召喚時コスト軽減の節を持つ。
- 差し戻し0件: summon_time_cost 単独は解消（0件）。
"""
import json
from pathlib import Path

import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent

REGISTERED = [
    "dmr15-002", "dmr18-027", "dmr18-031", "dmr18-033", "dmr18-040",
    "dmr19-025", "dmrp13-017", "dmrp13-037", "dm25ex3-rp4tr3",
    "dm26ex2-016", "dmrp22-5a",
]
BOUNCED = {}


def _converted():
    data = yaml.safe_load(
        (ROOT / "data" / "cards" / "converted.yaml").read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["cards"]}


def _rejects():
    return {json.loads(line)["id"]: json.loads(line) for line in
            (ROOT / "data" / "cards" / "raw" / "rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()}


def _opt_reduce_static(mod):
    return {"kind": "static", "affects": "self", "zone": "hand",
            "mod": {"opt_reduce": mod}}


# 第6弾の既存イディオム（T038/T039/T040型）
_REVEAL_EVO = _opt_reduce_static(
    {"amount": 2, "floor": 0, "do": {"select": {"zone": "hand", "owner": "you",
                                               "filter": {"types": ["evolution"]}, "other": True},
                                    "min": 1, "max": 1}})
_DISCARD_ONE = _opt_reduce_static(
    {"amount": 3, "floor": 0, "do": {"select": {"zone": "hand", "owner": "you", "other": True},
                                    "min": 1, "max": 1, "move_to": "graveyard"}})
_SPELLS_TO_DECK = _opt_reduce_static(
    {"amount": 1, "per": True, "floor": 1,
     "do": {"select": {"zone": "graveyard", "owner": "you", "filter": {"types": ["spell"]}},
            "min": 0, "max": 99, "move_to": "deck", "shuffle": True}})
# 第189弾の新形
_MULTI_SELECT = _opt_reduce_static(
    {"amount": 1, "per": True, "floor": 0,
     "do": {"selects": [{"select": {"zone": "hand", "owner": "you", "other": True}, "min": 0, "max": 1},
                        {"select": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"]}}, "min": 0, "max": 1},
                        {"select": {"zone": "bz", "owner": "you", "filter": {"types": ["tamaseed"]}}, "min": 0, "max": 1},
                        {"select": {"zone": "shield", "owner": "you"}, "min": 0, "max": 1}],
            "move_to": "graveyard"}})
_SHIELD_TO_HAND = _opt_reduce_static(
    {"amount": 3, "floor": 0,
     "do": {"select": {"zone": "shield", "owner": "you"}, "min": 1, "max": 1,
            "move_to": "hand", "strigger_off": True}})
_SHIELDS_FUEL = _opt_reduce_static(
    {"amount": 1, "per": True, "floor": 0,
     "do": {"select": {"zone": "shield", "owner": "you"}, "min": 0, "max": 2}})
_COST9_REVEAL = _opt_reduce_static(
    {"amount": 1, "per": True, "floor": 0,
     "do": {"select": {"zone": "hand", "owner": "you",
                       "filter": {"cost_le": 9, "cost_ge": 9}, "other": True},
            "min": 0, "max": 99}})

_FUEL_TO_HAND_CIP = {
    "kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "move", "select": {"ref": "fuel"}, "to": "hand",
                "reason": "return", "strigger": "off"}]}

ADDITIONS = {
    "dmr15-002": {
        "abilities": [_SPELLS_TO_DECK,
                      {"kind": "trigger",
                       "when": {"event": "cast",
                                "subject": {"owner": "you", "filter": {"types": ["spell"], "civs": ["water"]}}},
                       "effect": [{"op": "may", "body": [
                           {"op": "move", "select": {"zone": "bz", "owner": "any", "count": 1},
                            "to": "hand", "reason": "return"}]}]}],
        "keywords": ["triple_breaker"]},
    "dmr18-027": {
        "abilities": [_REVEAL_EVO,
                      {"kind": "trigger", "when": {"event": "turn_end", "player": "you"},
                       "effect": [{"op": "untap", "select": {"ref": "self"}}]}]},
    "dmr18-031": {"abilities": [_REVEAL_EVO]},
    "dmr18-033": {"abilities": [_REVEAL_EVO]},
    "dmr18-040": {"abilities": [_REVEAL_EVO]},
    "dmr19-025": {"abilities": [_COST9_REVEAL],
                  "keywords": ["blocker", "double_breaker"]},
    "dmrp13-017": {"abilities": [_SHIELD_TO_HAND]},
    "dmrp13-037": {"abilities": [_DISCARD_ONE]},
    "dm25ex3-rp4tr3": {"abilities": [_MULTI_SELECT]},
    "dm26ex2-016": {"abilities": [_SHIELDS_FUEL, _FUEL_TO_HAND_CIP]},
    "dmrp22-5a": {"abilities": [_MULTI_SELECT]},
}


def test_registered_have_summon_time_cost_clauses():
    conv = _converted()
    for cid in REGISTERED:
        assert cid in conv, cid
        d = parse_card(conv[cid], TABLES)
        assert d.id == cid
        for e in ADDITIONS[cid].get("abilities", []):
            assert e in d.abilities, f"{cid}: 節が無い: {e}"
        for kw in ADDITIONS[cid].get("keywords", []):
            assert kw in (d.keywords or []), f"{cid}: keyword 無い: {kw}"


def test_bounced_with_refined_gap():
    rej = _rejects()
    for cid, gaps in BOUNCED.items():
        assert cid in rej, cid
        assert rej[cid]["gaps"] == gaps, (cid, rej[cid]["gaps"])
    # summon_time_cost 単独は解消。
    assert not [r for r in rej.values()
                if r.get("gaps") == ["summon_time_cost"]]
