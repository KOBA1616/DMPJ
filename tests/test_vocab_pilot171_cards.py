"""第171弾 attack_redirect の再変換ラウンド207: 対象14件の生成と登録形の検証。

生成は rejects の partial に attack_redirect 語彙（起動型リダイレクト untap コスト
+ redirect、must_be_attacked、must_attack_creature）を足す決定的な変換。
14件すべて新規登録（差し戻しなし）。attack_redirect の単独ギャップは 0 残り
（dmrp07-012 は cost_reduction_enters_tapped との複合で残る）。
"""
import copy
import json
from pathlib import Path

import yaml

from dmsim.defs import load_tables, parse_card

ROOT = Path(__file__).parent.parent
BACKUP = Path.home() / "workspace/DMPJ-work/DMPJ-main.old-round201-20261110/data/cards/raw/rejects.jsonl"
TABLES = load_tables()

TARGETS = ["dm26rp3-053", "dmbd04-002", "dmr23-s01", "dmrp01-061",
           "dmrp03-062", "dmrp04s-058", "dmrp07-061", "dmrp09-066",
           "dmrp10-s02", "dmsd10-009", "dmsd10-010", "dmx17-s03",
           "dmx22a-005", "dm25ex4-s05"]
BOUNCED = {}
NOTES = "再変換ラウンド207。第171弾 attack_redirect の再変換。"


def _rows():
    out = {}
    for path in (ROOT / "data/cards/raw/rejects.jsonl", BACKUP):
        if not path.exists():
            continue
        for line in open(path):
            r = json.loads(line)
            out.setdefault(r["id"], r)
    return out


def _redirect(cost=None, if_=None):
    a = {"kind": "activate"}
    a["cost"] = cost if cost is not None else {"untap": "self"}
    if if_ is not None:
        a["if"] = if_
    a["redirect"] = True
    return a


REDIRECT = _redirect()
REDIRECT_TAPONLY = {"kind": "activate", "cost": {"untap": "self"},
                    "redirect": {"include_cost": False}}
REDIRECT_FILTER = _redirect(cost={"untap": {"types": ["creature"], "tapped": True}})
MORE_CREATURES = {"cmp": [{"count": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"]}}},
                         ">",
                         {"count": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}}}]}
REDIRECT_COND = _redirect(if_=MORE_CREATURES)

SHIELD_MORE = {"cmp": [{"count": {"zone": "shield", "owner": "you"}},
                       ">",
                       {"count": {"zone": "shield", "owner": "opp"}}]}


def _static(if_, affects, mod):
    a = {"kind": "static"}
    if if_ is not None:
        a["if"] = if_
    a["affects"] = affects
    a["mod"] = mod
    return a


def _tap_own_then(body_after):
    return {"kind": "trigger",
            "when": {"event": "move", "subject": "self", "to": "bz"},
            "effect": [{"op": "may", "body": [
                {"op": "choose",
                 "select": {"zone": "bz", "owner": "you",
                            "filter": {"types": ["creature"]}, "count": 1},
                 "as": "t"},
                {"op": "tap", "select": {"ref": "t", "count": "all"}},
                {"op": "if", "cond": {"exists": {"ref": "t"}},
                 "then": body_after}]}]}


def build():
    rows = _rows()
    cards = []
    for cid in TARGETS:
        if cid not in rows:
            continue
        row = rows[cid]
        card = copy.deepcopy(row["partial"])
        card["text"] = row["text"]
        card.setdefault("abilities", [])
        if cid == "dm26rp3-053":
            card["abilities"] += [REDIRECT]
        elif cid == "dmbd04-002":
            card["abilities"] += [REDIRECT,
                _static(SHIELD_MORE,
                        {"zone": "bz", "owner": "you", "other": True,
                         "filter": {"types": ["creature"], "races": ["メタリカ"]}},
                        {"deny": ["be_chosen"]})]
        elif cid == "dmr23-s01":
            card["abilities"] += [REDIRECT_TAPONLY,
                {"kind": "trigger",
                 "when": {"event": "turn_end", "player": "you"},
                 "effect": [{"op": "may", "body": [
                     {"op": "choose",
                      "select": {"zone": "bz", "owner": "you",
                                 "filter": {"types": ["creature"]}, "count": 1},
                      "as": "t"},
                     {"op": "tap", "select": {"ref": "t", "count": "all"}},
                     {"op": "if", "cond": {"exists": {"ref": "t"}},
                      "then": [{"op": "draw", "count": 1}]}]}]}]
        elif cid in ("dmrp01-061", "dmrp04s-058", "dmrp09-066"):
            card["abilities"] += [REDIRECT]
        elif cid == "dmrp03-062":
            card["abilities"] += [REDIRECT,
                {"kind": "trigger",
                 "when": {"event": "move", "to": "graveyard", "reason": "destroy",
                          "subject": "self"},
                 "effect": [{"op": "tap",
                             "select": {"zone": "bz", "owner": "opp",
                                        "filter": {"types": ["creature"]},
                                        "count": 1}}]}]
        elif cid == "dmrp07-061":
            card["abilities"] += [REDIRECT_COND]
        elif cid == "dmrp10-s02":
            card["abilities"] += [REDIRECT_FILTER,
                {"kind": "replace",
                 "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                                          "filter": {"types": ["creature"]}}},
                                ">=", 5]},
                 "when": {"event": "move", "from": "bz",
                          "to": ["hand", "mana", "deck", "shield"],
                          "subject": {"owner": "you",
                                      "filter": {"types": ["creature"]}}},
                 "instead": []}]
        elif cid == "dmsd10-009":
            card["abilities"] += [_tap_own_then(
                [{"op": "tap",
                  "select": {"zone": "bz", "owner": "opp",
                             "filter": {"types": ["creature"]}, "count": 1}}]),
                REDIRECT]
        elif cid == "dmsd10-010":
            card["abilities"] += [_tap_own_then([{"op": "draw", "count": 1}]),
                                  REDIRECT]
        elif cid == "dmx17-s03":
            card["abilities"] += [
                {"kind": "trigger",
                 "when": {"event": "attack", "subject": "self"},
                 "effect": [{"op": "may", "body": [
                     {"op": "move",
                      "select": {"zone": "hand", "owner": "you",
                                 "filter": {"types": ["creature"],
                                            "civs": ["nature"],
                                            "not_types": ["evolution"]},
                                 "count": 1},
                      "to": "bz", "reason": "put"}]}]},
                _static(None, "self", {"must_be_attacked": True})]
        elif cid == "dmx22a-005":
            card["keywords"] = ["guardman", "double_breaker"]
            card["abilities"] += [_static(
                {"exists": {"ref": "self", "filter": {"tapped": True}}},
                "self", {"must_be_attacked": True})]
        elif cid == "dm25ex4-s05":
            card["abilities"] += [_static(
                None, {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}},
                {"must_attack_creature": {"first_only": True}})]
        card["source"]["unsupported"] = []
        card["source"]["notes"] = NOTES
        card["source"]["review"] = "pending"
        cards.append(card)
    return {"cards": cards}


def test_build_forms_parse():
    built = build()["cards"]
    assert len(built) == len(TARGETS)
    for card in built:
        parse_card(card, TABLES)


def test_registered_forms():
    conv = {c["id"]: c for c in yaml.safe_load(open(ROOT / "data/cards/converted.yaml"))["cards"]}
    for cid in TARGETS:
        assert cid in conv, cid
    # 形の要点だけ確認する（詳細な挙動は test_vocab_pilot171.py の proto で検証済み）
    assert conv["dm26rp3-053"]["abilities"][0]["redirect"] is True
    assert conv["dm26rp3-053"]["abilities"][0]["cost"] == {"untap": "self"}
    assert conv["dmr23-s01"]["abilities"][0]["redirect"] == {"include_cost": False}
    assert conv["dmr23-s01"]["abilities"][1]["when"] == {"event": "turn_end", "player": "you"}
    assert conv["dmrp07-061"]["abilities"][0]["if"]["cmp"][1] == ">"
    assert conv["dmrp10-s02"]["abilities"][1]["cost"] == {"untap": {"types": ["creature"], "tapped": True}}
    assert conv["dmrp10-s02"]["abilities"][2]["kind"] == "replace"
    assert conv["dmrp10-s02"]["abilities"][2]["instead"] == []
    assert conv["dmbd04-002"]["abilities"][1]["mod"] == {"deny": ["be_chosen"]}
    assert conv["dmbd04-002"]["abilities"][1]["affects"]["other"] is True
    assert conv["dmrp03-062"]["abilities"][1]["when"]["reason"] == "destroy"
    assert conv["dmx17-s03"]["abilities"][1]["mod"] == {"must_be_attacked": True}
    assert conv["dmx22a-005"]["keywords"] == ["guardman", "double_breaker"]
    assert conv["dm25ex4-s05"]["abilities"][-1]["mod"] == {"must_attack_creature": {"first_only": True}}
    assert conv["dmsd10-009"]["abilities"][0]["effect"][0]["body"][2]["then"][0]["op"] == "tap"
    assert conv["dmsd10-010"]["abilities"][0]["effect"][0]["body"][2]["then"][0]["op"] == "draw"


def test_round207_not_in_rejects():
    rows = [json.loads(line) for line in open(ROOT / "data/cards/raw/rejects.jsonl")
            if line.strip()]
    ids = {r["id"] for r in rows}
    for cid in TARGETS:
        assert cid not in ids, cid
