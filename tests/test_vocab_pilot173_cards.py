"""第173弾 deck_evolution の再変換ラウンド209: 対象13件の生成と登録形の検証。

生成は rejects の partial に deck_evolution / evo_source 語彙を足す決定的な
変換（answers/gen_round209.py と同一）。11件新規登録、2件は G・リンク
未対応のため差し戻し（deck_evolution＋メテオバーンの解決済み節は partial
に残る）。deck_evolution の単独ギャップは 0 残り。
"""
import copy
import _conv_cache  # noqa: E402
import json
import subprocess
from pathlib import Path

import yaml

from dmsim.cards.defs import load_tables, parse_card

ROOT = Path(__file__).parent.parent
# reopen 前の rejects は第173弾コミットの親ツリーに残っている
PILOT_COMMIT = "acd8dec"
TABLES = load_tables()

NOTES = "再変換ラウンド209。第173弾 deck_evolution の再変換。"
NOTES_BOUNCE = NOTES + "G・リンクは未対応のため差し戻し（deck_evolution＋メテオバーンは解決済み）。"

TARGETS = ["dm32-029", "dm32-061", "dm33-031", "dm35-048", "dmc56-003",
           "dmc58-003", "dmc64-026", "dmc64-036", "dmc64-042", "dmex03-016",
           "dmex17-037", "dmrp17-023", "promoy8-002"]
BOUNCE = {"dmc58-003", "dmex17-037"}
REGISTERED = [t for t in TARGETS if t not in BOUNCE]


def _rows():
    out = subprocess.check_output(
        ["git", "show", f"{PILOT_COMMIT}:data/cards/raw/rejects.jsonl"],
        cwd=ROOT, text=True)
    return {json.loads(line)["id"]: json.loads(line)
            for line in out.splitlines() if line.strip()}


def _base(cid, rows, bounce=False):
    row = rows[cid]
    p = copy.deepcopy(row["partial"])
    card = {"id": p["id"], "name": p["name"],
            "types": list(p["types"]), "civs": list(p["civs"]),
            "cost": p["cost"], "mana": p["mana"],
            "text": row["text"],
            "source": {"official": p["id"], "review": "pending",
                       "notes": NOTES_BOUNCE if bounce else NOTES,
                       "unsupported": []}}
    if "power" in p:
        card["power"] = p["power"]
    if "races" in p:
        card["races"] = list(p["races"])
    if "keywords" in p:
        card["keywords"] = list(p["keywords"])
    if "evolve_from" in p:
        card["evolve_from"] = copy.deepcopy(p["evolve_from"])
    if "aliases" in p.get("source", {}):
        card["source"]["aliases"] = list(p["source"]["aliases"])
    return card


def _deck_evo(card, count=1, rest_to=None, blind=False, shuffle_first=False):
    de = {"count": count}
    if rest_to:
        de["rest_to"] = rest_to
    if blind:
        de["blind"] = True
    if shuffle_first:
        de["shuffle_first"] = True
    card["types"] = ["creature", "evolution"]
    card["evolve_from"] = {"types": ["creature"]}
    card["deck_evolution"] = de
    return card


def _cip_attack_untapped():
    return {"kind": "trigger",
            "when": {"event": "move", "to": "bz", "subject": "self"},
            "effect": [{"op": "modify", "select": {"ref": "self"},
                        "mod": {"allow": [{"action": "attack_creature",
                                           "other": {"tapped": False}}]},
                        "duration": "end_of_turn"}]}


def _meteor_burn_destroy_self_power():
    return {"kind": "trigger",
            "when": {"event": "attack", "subject": "self"},
            "effect": [{"op": "may", "body": [
                {"op": "move", "select": {"under_of": "self", "count": 1},
                 "to": "graveyard", "reason": "put", "as": "paid"},
                {"op": "if", "cond": {"exists": {"ref": "paid"}},
                 "then": [{"op": "destroy",
                           "select": {"zone": "bz", "owner": "opp",
                                      "filter": {"types": ["creature"],
                                                 "power_le": {"sum": [{"power_of": {"ref": "self"}}, -1]}},
                                      "count": "all"}}]}]}]}


def _meteor_burn_play_free_from_mana():
    return {"kind": "trigger",
            "when": {"event": "attack", "subject": "self"},
            "effect": [{"op": "may", "body": [
                {"op": "move", "select": {"under_of": "self", "count": 1},
                 "to": "graveyard", "reason": "put", "as": "paid"},
                {"op": "if", "cond": {"exists": {"ref": "paid"}},
                 "then": [{"op": "play_free",
                           "select": {"zone": "mana", "owner": "you",
                                      "filter": {"types": ["spell"],
                                                 "civs": ["fire", "darkness"],
                                                 "cost_le": 6},
                                      "count": 1}}]}]}]}


def _meteor_burn_play_free_paid():
    return {"kind": "trigger",
            "when": {"event": "attack", "subject": "self"},
            "effect": [{"op": "may", "body": [
                {"op": "move", "select": {"under_of": "self", "count": 1},
                 "to": "graveyard", "reason": "put", "as": "paid"},
                {"op": "if",
                 "cond": {"exists": {"ref": "paid",
                                     "filter": {"types": ["spell"],
                                                "civs": ["fire", "darkness"]}}},
                 "then": [{"op": "play_free",
                           "select": {"ref": "paid", "count": 1}}]}]}]}


def _activate_stack_search(name_has):
    return {"kind": "activate", "cost": {"tap": "self"},
            "effect": [{"op": "may", "body": [
                {"op": "choose",
                 "select": {"zone": "deck", "owner": "you", "look": True,
                            "filter": {"name_has": name_has}, "count": 1},
                 "as": "p"},
                {"op": "move", "select": {"ref": "p", "count": "all"},
                 "to": "bz", "reason": "put",
                 "stack_evo": True, "evo_source": {"ref": "self"}}]},
                {"op": "shuffle"}]}


def build():
    rows = _rows()
    cards = []

    c = _deck_evo(_base("dm32-029", rows))
    c["abilities"] = [{"kind": "static", "affects": "self",
                       "if": {"exists": {"zone": "bz", "owner": "you",
                                         "filter": {"races": ["アーマード・ドラゴン"]},
                                         "other": True}},
                       "mod": {"power": 3000}}]
    cards.append(c)

    c = _deck_evo(_base("dm32-061", rows))
    c["abilities"] = [_cip_attack_untapped()]
    cards.append(c)

    cards.append(_deck_evo(_base("dm33-031", rows)))
    cards.append(_deck_evo(_base("dm35-048", rows)))

    c = _deck_evo(_base("dmc56-003", rows))
    c["abilities"] = [
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz", "subject": "self"},
         "effect": [{"op": "choose",
                     "select": {"zone": "deck", "owner": "you", "count": "all"},
                     "as": "deck"},
                    {"op": "may", "body": [
                        {"op": "move",
                         "select": {"ref": "deck",
                                    "filter": {"name_has": "紫電・ドラゴン"},
                                    "count": 1},
                         "to": "hand", "reason": "return"}]},
                    {"op": "shuffle", "player": "you"}]},
        {"kind": "static",
         "affects": {"zone": "bz", "owner": "you",
                     "filter": {"name_has": "紫電・ドラゴン"}},
         "mod": {"grant": ["speed_attacker"]}}]
    cards.append(c)

    c = _deck_evo(_base("dmc58-003", rows, bounce=True),
                  count=3, rest_to="graveyard")
    c["keywords"] = ["left_g_link"]
    c["abilities"] = [_meteor_burn_play_free_from_mana()]
    c["source"]["unsupported"] = [
        {"need": "g_link",
         "text": "G・リンク《邪神R・ロマノフ》または《邪神C・ロマノフ》の左横。"}]
    cards.append(c)

    c = _deck_evo(_base("dmc64-026", rows))
    c["abilities"] = [{"kind": "trigger",
                       "when": {"event": "move", "from": "bz", "to": "graveyard",
                                "reason": "destroy", "from_under": "self"},
                       "effect": [{"op": "may", "body": [
                           {"op": "move",
                            "select": {"ref": "event.subject", "zone": "graveyard"},
                            "to": "bz", "reason": "put"}]}]}]
    cards.append(c)

    c = _base("dmc64-036", rows)
    c["abilities"] = [_activate_stack_search("ケンゴウグレンオー")]
    cards.append(c)

    c = _base("dmc64-042", rows)
    c["abilities"] = [_activate_stack_search("ワンケングレンオー")]
    cards.append(c)

    c = _deck_evo(_base("dmex03-016", rows))
    c["abilities"] = [_meteor_burn_destroy_self_power()]
    cards.append(c)

    c = _deck_evo(_base("dmex17-037", rows, bounce=True),
                  count=1, blind=True, shuffle_first=True)
    c["keywords"] = ["left_g_link"]
    c["abilities"] = [_meteor_burn_play_free_paid()]
    c["source"]["unsupported"] = [
        {"need": "g_link",
         "text": "左G・リンクOMG：《邪神・Rロマノフ》、《邪神C・ロマノフ》、「中央G・リンク」または「右G・リンク」を持つゴッドの左横"}]
    cards.append(c)

    c = _base("dmrp17-023", rows)
    c["abilities"] = [{"kind": "trigger",
                       "when": {"event": "move", "to": "bz", "subject": "self"},
                       "effect": [{"op": "choose",
                                   "select": {"zone": "deck", "owner": "you",
                                              "from_top": 4, "look": True, "count": "all"},
                                   "as": "pile"},
                                  {"op": "may", "body": [
                                      {"op": "choose",
                                       "select": {"ref": "pile",
                                                  "filter": {"types": ["evolution"],
                                                             "cost_le": 6},
                                                  "count": 1},
                                       "as": "evo"},
                                      {"op": "move",
                                       "select": {"ref": "evo", "count": "all"},
                                       "to": "bz", "reason": "put",
                                       "stack_evo": True,
                                       "evo_source": {"ref": "self"}}]},
                                  {"op": "move",
                                   "select": {"ref": "pile", "zone": "deck", "count": "all"},
                                   "to": "deck", "position": "bottom",
                                   "order": "choose", "reason": "put"}]}]
    cards.append(c)

    c = _deck_evo(_base("promoy8-002", rows))
    c["abilities"] = [{"kind": "replace",
                       "when": {"event": "break",
                                "subject": {"owner": "you",
                                            "filter": {"races": ["ファイアー・バード"]}}},
                       "if": {"exists": {"ref": "shield",
                                         "filter": {"keyword": "s_trigger"}}},
                       "instead": [{"op": "move",
                                    "select": {"ref": "event.shield", "count": 1},
                                    "to": "graveyard", "reason": "put"}]}]
    cards.append(c)

    assert [c["id"] for c in cards] == TARGETS
    return {"cards": cards}


def test_build_forms_parse():
    built = build()["cards"]
    assert len(built) == len(TARGETS)
    for card in built:
        parse_card(card, TABLES)


def test_registered_forms():
    built = {c["id"]: c for c in build()["cards"]}
    conv = {c["id"]: c for c in _conv_cache.all_cards(ROOT / "data/cards/converted.yaml")}
    for cid in REGISTERED:
        assert cid in conv, cid
        assert conv[cid] == built[cid], cid
    # 形の要点だけ確認する（詳細な挙動は test_vocab_pilot173.py の proto で検証済み）
    assert conv["dm32-029"]["deck_evolution"] == {"count": 1}
    assert conv["dmc56-003"]["abilities"][1]["mod"] == {"grant": ["speed_attacker"]}
    assert conv["dmc64-036"]["abilities"][0]["effect"][0]["body"][1]["evo_source"] == {"ref": "self"}
    assert conv["dmrp17-023"]["abilities"][0]["effect"][0]["select"]["from_top"] == 4


def test_bounced_forms_banked():
    # 第173弾で差し戻した2枚は第250弾（G・リンク一般化）＋ラウンド284で登録済み。
    # 登録形の検証は test_vocab_pilot250_cards.py が担う。
    rows = {json.loads(line)["id"]: json.loads(line)
            for line in open(ROOT / "data/cards/raw/rejects.jsonl") if line.strip()}
    conv_ids = {c["id"] for c in _conv_cache.all_cards(ROOT / "data/cards/converted.yaml")}
    for cid in BOUNCE:
        assert cid in conv_ids, cid
        assert cid not in rows, cid


def test_round209_not_in_rejects():
    rows = [json.loads(line) for line in open(ROOT / "data/cards/raw/rejects.jsonl")
            if line.strip()]
    ids = {r["id"] for r in rows}
    for cid in REGISTERED:
        assert cid not in ids, cid
    assert not any("deck_evolution" in (r.get("gaps") or []) for r in rows)
