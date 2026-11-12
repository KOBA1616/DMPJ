"""第167弾 G・G・G の再変換ラウンド203: 対象17件の生成と登録形の検証。

生成は rejects の partial に G・G・G の条件つき能力を足す決定的な変換。
条件は {cmp: [{count: {zone: hand, owner: you}}, "<=", 1]}（T271 の型）。
dmrp06-s08 / dmrp08-008 / dmrp08-047 は残りの節が別語彙のため、解けた分を
partial に残して差し戻す（unsupported を差し替える）。
"""
import json
from pathlib import Path

import yaml

from dmsim.defs import load_tables, parse_card

ROOT = Path(__file__).parent.parent
from _rejects_snapshot import snapshot_path
BACKUP = snapshot_path()
TABLES = load_tables()

HAND_LE_1 = {"cmp": [{"count": {"zone": "hand", "owner": "you"}}, "<=", 1]}
HAND_GT_1 = {"cmp": [{"count": {"zone": "hand", "owner": "you"}}, ">", 1]}
HAND_EQ_1 = {"cmp": [{"count": {"zone": "hand", "owner": "you"}}, "==", 1]}

TARGETS = ["dmex02-050", "dmex02-054", "dmex03-s07", "dmex07-m08", "dmrp06-050",
           "dmrp06-083", "dmrp06-084", "dmrp06-s08", "dmrp07-022", "dmrp07-047",
           "dmrp07-084", "dmrp07-s08", "dmrp08-008", "dmrp08-025", "dmrp08-047",
           "dmrp08-085", "dmrp08-087"]
BOUNCED = {"dmrp06-s08": "attack_target_unchangeable",
           "dmrp08-008": "top_card_play_permission",
           "dmrp08-047": "per_creature_battle"}
NOTES = "再変換ラウンド203。第167弾 G・G・G の再変換。"


def _rows():
    out = {}
    for path in (ROOT / "data/cards/raw/rejects.jsonl", BACKUP):
        if not path.exists():
            continue
        for line in open(path):
            r = json.loads(line)
            out.setdefault(r["id"], r)
    return out


def _ggg_static(mod, **kw):
    d = {"kind": "static", "affects": "self", "if": HAND_LE_1, "mod": mod}
    d.update(kw)
    return d


def _ggg_attack_trigger(effect):
    return {"kind": "trigger", "when": {"event": "attack", "subject": "self"},
            "if": HAND_LE_1, "effect": effect}


def _destroy_opp_blocker():
    return [{"op": "destroy",
             "select": {"zone": "bz", "owner": "opp",
                        "filter": {"types": ["creature"], "keyword": "blocker"}, "count": 1}}]


def _destroy_opp_power_le(n):
    return [{"op": "destroy",
             "select": {"zone": "bz", "owner": "opp",
                        "filter": {"types": ["creature"], "power_le": n}, "count": 1}}]


def build():
    rows = _rows()
    cards = []
    for cid in TARGETS:
        if cid not in rows:
            continue
        row = rows[cid]
        card = json.loads(json.dumps(row["partial"]))
        card["text"] = row["text"]
        card.setdefault("abilities", [])
        unsup = [u for u in card.get("source", {}).get("unsupported", [])
                 if u.get("need") != "g_g_g"]
        if cid == "dmex02-050":
            card["abilities"] += [
                _ggg_static({"grant": ["speed_attacker"]}),
                {"kind": "trigger", "when": {"event": "move", "subject": "self", "to": "bz"},
                 "effect": [{"op": "may", "body": [
                     {"op": "choose", "select": {"zone": "hand", "owner": "you", "count": 1},
                      "as": "keep"},
                     {"op": "if", "cond": {"exists": {"ref": "keep"}}, "then": [
                         {"op": "move",
                          "select": {"zone": "hand", "owner": "you", "count": "all",
                                     "exclude": {"ref": "keep"}},
                          "to": "graveyard", "reason": "discard"},
                         {"op": "delayed_trigger", "when": {"event": "turn_end"},
                          "effect": [{"op": "draw", "count": 2}]}]}]}]}]
        elif cid == "dmex02-054":
            card["abilities"] += [_ggg_static({"grant": ["speed_attacker"]})]
        elif cid == "dmex03-s07":
            card["abilities"] += [
                {"kind": "trigger", "when": {"event": "attack", "subject": "self"},
                 "if": HAND_LE_1,
                 "effect": [{"op": "untap", "select": {"ref": "self"}},
                            {"op": "draw", "count": 2}]},
                {"kind": "static", "affects": "self",
                 "mod": {"battle_power": {"amount": 5000}}}]
        elif cid == "dmex07-m08":
            card["free_if"] = HAND_EQ_1
            card["spell"] = [
                {"op": "destroy",
                 "select": {"zone": "bz", "owner": "opp",
                            "filter": {"types": ["creature"], "power_le": 3000}, "count": "all"}},
                {"op": "if",
                 "cond": {"exists": {"zone": "mana", "owner": "you",
                                     "filter": {"civs": ["fire"]}}},
                 "then": [{"op": "draw", "count": 1}]}]
        elif cid == "dmrp06-050":
            # partial の誘発形パワーアタッカーを標準の power_when 形に正す
            card["abilities"] = [
                {"kind": "static", "affects": "self",
                 "mod": {"power_when": {"amount": 2000, "when": "attacking"}}},
                {"kind": "static", "affects": "self", "if": HAND_GT_1,
                 "mod": {"deny": ["attack_player", "attack_creature"]}}]
        elif cid == "dmrp06-083":
            card["abilities"] += [_ggg_attack_trigger(_destroy_opp_blocker())]
        elif cid == "dmrp06-084":
            card["abilities"] += [_ggg_static(
                {"power_when": {"amount": 5000, "when": "attacking"},
                 "grant": ["double_breaker"]})]
        elif cid == "dmrp06-s08":
            card["abilities"] += [
                _ggg_static({"battle_power": {"amount": 10000, "only": "attacking"}}),
                {"kind": "replace", "zone": "hand", "optional": True,
                 "when": {"event": "move", "from": "hand", "to": "graveyard",
                          "reason": "discard", "subject": "self", "by": "opp",
                          "cause": {"kind": "spell"}},
                 "instead": [{"op": "move", "select": {"ref": "self", "count": 1},
                              "to": "bz", "reason": "put"}]},
                {"kind": "replace", "zone": "hand", "optional": True,
                 "when": {"event": "move", "from": "hand", "to": "graveyard",
                          "reason": "discard", "subject": "self", "by": "opp",
                          "cause": {"kind": "ability"}},
                 "instead": [{"op": "move", "select": {"ref": "self", "count": 1},
                              "to": "bz", "reason": "put"}]}]
            unsup.append({"need": "attack_target_unchangeable",
                          "text": "このクリーチャーの攻撃先は変更できない。"})
        elif cid == "dmrp07-022":
            card["abilities"] += [_ggg_attack_trigger(_destroy_opp_power_le(5000))]
        elif cid == "dmrp07-047":
            card["abilities"] += [
                {"kind": "static",
                 "affects": {"zone": "hand", "owner": "you",
                             "filter": {"types": ["creature"], "races": ["ビートジョッキー"]}},
                 "if": HAND_LE_1, "mod": {"cost": -2}}]
        elif cid == "dmrp07-084":
            card["abilities"] += [_ggg_static({"battle_indestructible": True})]
        elif cid == "dmrp07-s08":
            card["abilities"] += [
                {"kind": "static",
                 "affects": {"zone": "hand", "owner": "you",
                             "filter": {"types": ["creature"], "races": ["ビートジョッキー"]}},
                 "if": HAND_LE_1, "mod": {"cost": -5}},
                {"kind": "trigger",
                 "when": {"event": "move", "to": "bz",
                          "subject": {"owner": "you",
                                      "filter": {"types": ["creature"],
                                                 "races": ["ビートジョッキー"]},
                                      "other": True}},
                 "effect": [{"op": "may", "body": [{"op": "draw", "count": 1}]}]}]
        elif cid == "dmrp08-008":
            card["abilities"] += [
                {"kind": "trigger", "when": {"event": "move", "subject": "self", "to": "bz"},
                 "effect": [{"op": "move",
                             "select": {"zone": "hand", "owner": "you", "count": "all"},
                             "to": "graveyard", "reason": "discard"}]}]
            unsup.append({"need": "top_card_play_permission",
                          "text": "G・G・G：自分の手札が１枚以下なら、自分の山札の上から１枚目を見てもよい。自分のターン中、攻撃する前ならいつでも、そのカードがクリーチャーなら召喚してもよい。それが呪文なら唱えてもよい。（コストは支払う）"})
        elif cid == "dmrp08-025":
            card["spell"] = [
                {"op": "if", "cond": HAND_LE_1,
                 "then": [{"op": "destroy",
                           "select": {"zone": "bz", "owner": "opp",
                                      "filter": {"types": ["creature"], "power_le": 5000},
                                      "count": "all"}}],
                 "else": _destroy_opp_power_le(5000)}]
        elif cid == "dmrp08-047":
            card["spell"] = [
                {"op": "choose",
                 "select": {"zone": "bz", "owner": "you",
                            "filter": {"types": ["creature"]}, "count": 1},
                 "as": "c"},
                {"op": "modify", "select": {"ref": "c"}, "mod": {"power": 2000},
                 "duration": "end_of_turn"},
                {"op": "choose",
                 "select": {"zone": "bz", "owner": "opp",
                            "filter": {"types": ["creature"]}, "count": 1},
                 "as": "d"},
                {"op": "force_battle", "a": {"ref": "c"}, "b": {"ref": "d"}}]
            unsup.append({"need": "per_creature_battle",
                          "text": "G・G・G：自分の手札が１枚以下なら、このターン、自分のクリーチャー１体を+2000するかわりに、自分のクリーチャーすべてのパワーを+4000する。これらのクリーチャー１体につき相手のクリーチャーを１体選び、その２体をバトルさせる。"})
        elif cid == "dmrp08-085":
            card["abilities"] += [_ggg_static({"battle_power": {"amount": 3000}})]
        elif cid == "dmrp08-087":
            card["spell"] = [
                {"op": "if", "cond": HAND_LE_1,
                 "then": [{"op": "modify",
                           "select": {"zone": "bz", "owner": "opp",
                                      "filter": {"types": ["creature"]}, "count": "all"},
                           "mod": {"require": ["attack"]},
                           "duration": "until_next_own_turn_start"}],
                 "else": [{"op": "choose",
                           "select": {"zone": "bz", "owner": "opp",
                                      "filter": {"types": ["creature"]}, "count": 1},
                           "as": "c"},
                          {"op": "modify", "select": {"ref": "c"},
                           "mod": {"require": ["attack"]},
                           "duration": "until_next_own_turn_start"}]}]
        card["source"]["unsupported"] = unsup
        card["source"]["notes"] = NOTES + ("" if cid not in BOUNCED else
                                           f"残りの節は {BOUNCED[cid]} のため差し戻し。")
        card["source"]["review"] = "pending"
        cards.append(card)
    return {"cards": cards}


def test_build_forms_parse():
    built = build()["cards"]
    rows = _rows()
    for card in built:
        if card["id"] not in rows:
            continue
        parse_card(card, TABLES)


def test_registered_forms():
    conv = {c["id"]: c for c in yaml.safe_load(open(ROOT / "data/cards/converted.yaml"))["cards"]}
    for cid in TARGETS:
        if cid in BOUNCED:
            assert cid not in conv
            continue
        assert cid in conv, cid
