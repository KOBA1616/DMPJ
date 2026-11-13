"""第170弾 crossed_state の再変換ラウンド206: 対象17件の生成と登録形の検証。

生成は rejects の partial に crossed_state 語彙（フィルタ crossed / crossed_ge /
crossed_le / crossed_name、セレクタ crossed_to / host_of、式 crossed_count /
crossed_ge、op uncross、mod breaks_add 辞書形、activate cost tap {ref: crossed}）
を足す決定的な変換。17件すべて新規登録（差し戻しなし）。
dm31-027 は partial が無いため原文から全文を構築する。
"""
import copy
import json
from pathlib import Path

import yaml

from dmsim.cards.defs import load_tables, parse_card

ROOT = Path(__file__).parent.parent
from _rejects_snapshot import snapshot_path
BACKUP = snapshot_path()
TABLES = load_tables()

TARGETS = ["dm30-030", "dm30-054", "dm31-037", "dmc42-050", "dmc64-002",
           "dm31-027", "dm31-039", "dm15-014", "dm16-013", "dm16-022",
           "dm16-026", "dm16-030", "dm16-034", "dm16-035", "dm17-001",
           "dm17-002", "dm17-012"]
BOUNCED = {}
NOTES = "再変換ラウンド206。第170弾 crossed_state の再変換。"


# 対象は後のラウンドで rejects から抜けたので、対象を含む main 上の版から読む（BACKUP も併用）
PILOT_COMMIT = "194b05c"


def _rows():
    import subprocess
    out = {}
    text = subprocess.check_output(["git", "show", f"{PILOT_COMMIT}:data/cards/raw/rejects.jsonl"], cwd=ROOT, text=True)
    for line in text.splitlines():
        if line.strip():
            r = json.loads(line)
            out.setdefault(r["id"], r)
    if BACKUP.exists():
        for line in open(BACKUP):
            r = json.loads(line)
            out.setdefault(r["id"], r)
    return out


def _static(if_, affects, mod):
    a = {"kind": "static"}
    if if_ is not None:
        a["if"] = if_
    a["affects"] = affects
    a["mod"] = mod
    return a


NOT_CROSSED = {"exists": {"ref": "self", "filter": {"crossed": False}}}
SAME_RACE = {"races": {"races_of": "crossed"}}


def build():
    rows = _rows()
    cards = []
    for cid in TARGETS:
        if cid == "dm31-027":
            # partial が無いため原文から全文を構築する
            row = rows[cid]
            card = {"id": "dm31-027", "name": "邪戦将ヒゲマロ",
                    "types": ["creature"], "civs": ["darkness"], "cost": 5,
                    "power": 3000, "races": ["サムライ", "ダークロード"], "mana": 1,
                    "text": row["text"],
                    "source": {"official": "dm31-027", "review": "pending",
                               "notes": NOTES, "unsupported": []},
                    "abilities": [
                        {"kind": "trigger",
                         "when": {"event": "move", "subject": "self", "to": "bz"},
                         "effect": [{"op": "may", "body": [
                             {"op": "play_free",
                              "select": {"zone": "hand", "owner": "you",
                                         "filter": {"types": ["cross_gear"]},
                                         "count": 1}}]}]},
                        _static(None, {"zone": "bz", "owner": "you",
                                       "filter": {"crossed": True}},
                                {"grant": ["slayer"]}),
                    ]}
            cards.append(card)
            continue
        if cid not in rows:
            continue
        row = rows[cid]
        card = copy.deepcopy(row["partial"])
        card["text"] = row["text"]
        card.setdefault("abilities", [])
        if cid == "dm30-030":
            card["types"] = ["creature", "evolution"]
            card["evolve_from"] = {"races": ["サムライ"]}
            card["abilities"] += [_static(
                {"exists": {"ref": "self", "filter": {"tapped": True}}},
                {"zone": "bz", "owner": "you", "filter": {"crossed": True}},
                {"breaks_add": 1})]
        elif cid in ("dm30-054", "dm31-037"):
            card["abilities"] += [_static(NOT_CROSSED, "self", {"deny": ["attack_player"]})]
        elif cid == "dmc42-050":
            card["spell"] = [
                {"op": "move",
                 "select": {"zone": "bz", "owner": "opp",
                            "filter": {"types": ["cross_gear"]}, "count": 1},
                 "to": "graveyard", "reason": "put", "as": "g"},
                {"op": "destroy", "select": {"host_of": "g",
                                             "filter": {"power_le": 2000}}},
            ]
        elif cid == "dmc64-002":
            card["abilities"] += [
                {"kind": "trigger",
                 "when": {"event": "move", "subject": "self", "to": "bz"},
                 "effect": [
                     {"op": "repeat", "times": 3,
                      "body": [{"op": "may", "body": [
                          {"op": "move",
                           "select": {"zone": "deck", "owner": "you", "from_top": 1},
                           "to": "graveyard", "reason": "put"}]}]},
                     {"op": "may", "body": [
                         {"op": "move",
                          "select": {"zone": "graveyard", "owner": "you",
                                     "filter": {"types": ["cross_gear"]}, "count": 1},
                          "to": "bz", "reason": "put"}]},
                 ]},
                _static(NOT_CROSSED, "self", {"deny": ["attack_creature"]}),
            ]
        elif cid == "dm31-039":
            card["abilities"] += [_static(
                None, "crossed",
                {"power": {"amount": 1000, "count": {"crossed_to": "self"}}})]
        elif cid == "dm15-014":
            card["abilities"] += [
                {"kind": "activate", "cost": {"tap": {"ref": "crossed"}},
                 "effect": [{"op": "destroy",
                             "select": {"zone": "bz", "owner": "any",
                                        "filter": {"power_le": {"power_of": {"ref": "crossed"}}},
                                        "count": "all"}}]},
            ]
        elif cid == "dm16-013":
            card["spell"] = [
                {"op": "destroy",
                 "select": {"zone": "bz", "owner": "any",
                            "filter": {"types": ["creature"], "crossed": True},
                            "count": "all"}},
            ]
        elif cid == "dm16-022":
            card["free_if"] = {"exists": {"zone": "bz", "owner": "any",
                                          "filter": {"crossed": True}}}
            card["abilities"] += [_static(
                None, {"zone": "bz", "owner": "any", "filter": {"crossed": True}},
                {"power": 1000})]
        elif cid == "dm16-026":
            card["abilities"] += [
                _static(None, {"zone": "bz", "owner": "any", "filter": SAME_RACE},
                        {"power": 1000}),
                {"kind": "trigger",
                 "when": {"event": "attack", "subject": {"filter": SAME_RACE}},
                 "effect": [{"op": "may", "body": [{"op": "draw", "count": 1}]}]},
            ]
        elif cid == "dm16-030":
            card["abilities"] += [_static(
                None, "self",
                {"allow": [{"action": "attack_creature",
                            "other": {"crossed": True, "tapped": False}}]})]
        elif cid == "dm16-034":
            card["spell"] = [
                {"op": "choose",
                 "select": {"zone": "bz", "owner": "opp",
                            "filter": {"types": ["creature"]}, "count": 1},
                 "as": "c"},
                {"op": "move", "select": {"crossed_to": "c", "count": "all"},
                 "to": "mana", "reason": "put"},
                {"op": "move", "select": {"ref": "c"}, "to": "mana", "reason": "put"},
            ]
        elif cid == "dm16-035":
            card["abilities"] += [_static(
                None, {"zone": "bz", "owner": "any", "filter": SAME_RACE},
                {"power": 2000})]
        elif cid == "dm17-001":
            card["abilities"] += [_static(
                {"exists": {"ref": "crossed",
                           "filter": {"crossed_name": "ロード・オブ・レジェンドソード"}}},
                "crossed", {"power": 8000})]
        elif cid == "dm17-002":
            card["abilities"] += [_static(
                {"exists": {"ref": "crossed",
                           "filter": {"crossed_name": "クイーン・オブ・プロテクション"}}},
                "crossed", {"breaks_add": 2})]
        elif cid == "dm17-012":
            card["abilities"] += [
                {"kind": "trigger",
                 "when": {"event": "move", "subject": "self", "to": "bz"},
                 "effect": [{"op": "uncross",
                             "select": {"zone": "bz", "owner": "any",
                                        "filter": {"types": ["cross_gear"],
                                                   "crossed": True},
                                        "count": "all"}}]},
            ]
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
    # 形の要点だけ確認する（詳細な挙動は test_vocab_pilot170.py の proto で検証済み）
    assert conv["dm30-030"]["abilities"][0]["mod"] == {"breaks_add": 1}
    assert conv["dm30-054"]["abilities"][0]["mod"] == {"deny": ["attack_player"]}
    assert conv["dm15-014"]["abilities"][0]["cost"] == {"tap": {"ref": "crossed"}}
    assert conv["dm16-013"]["spell"][0]["op"] == "destroy"
    assert conv["dm16-022"]["free_if"]["exists"]["filter"] == {"crossed": True}
    assert conv["dm16-034"]["spell"][1]["select"] == {"crossed_to": "c", "count": "all"}
    assert conv["dm17-012"]["abilities"][0]["effect"][0]["op"] == "uncross"
    assert len(conv["dm17-001"]["abilities"]) == 2
    assert conv["dm17-001"]["abilities"][1]["mod"] == {"power": 8000}
    assert conv["dm17-002"]["abilities"][1]["mod"] == {"breaks_add": 2}
    assert conv["dm31-027"]["abilities"][1]["mod"] == {"grant": ["slayer"]}
    assert conv["dm31-039"]["abilities"][0]["mod"]["power"]["count"] == {"crossed_to": "self"}


def test_round206_not_in_rejects():
    rows = [json.loads(line) for line in open(ROOT / "data/cards/raw/rejects.jsonl")
            if line.strip()]
    ids = {r["id"] for r in rows}
    for cid in TARGETS:
        assert cid not in ids, cid
