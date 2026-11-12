"""第168弾 フォートE の再変換ラウンド204: 対象15件の生成と登録形の検証。

生成は rejects の partial にフォートEの能力を足す決定的な変換。
得る能力は能力フラグ fort_e: {races: [...], as?: 変数名} で示す（第168弾）。
「タップした〜のいずれかよりパワーが小さい」は power_of（複数参照で最大値）を当て、
power_le: {sum: [power_of, -1]} で書く。
"""
import json
from pathlib import Path

import yaml

from dmsim.defs import load_tables, parse_card

ROOT = Path(__file__).parent.parent
from _rejects_snapshot import snapshot_path
BACKUP = snapshot_path()
TABLES = load_tables()

TARGETS = ["dm20-015", "dm20-021", "dm20-024", "dm20-048", "dm20-052", "dm20-s03",
           "dm21-010", "dm21-017", "dm22-040", "dm24ex1-039", "dmx12b-059",
           "promoy5-034", "sp-017", "dm20-006", "dm20-009"]
BOUNCED = {}
NOTES = "再変換ラウンド204。第168弾 フォートE の再変換。"


def _rows():
    out = {}
    for path in (ROOT / "data/cards/raw/rejects.jsonl", BACKUP):
        if not path.exists():
            continue
        for line in open(path):
            r = json.loads(line)
            out.setdefault(r["id"], r)
    return out


def _fe_trigger(races, effect, as_=None):
    fe = {"races": races}
    if as_:
        fe["as"] = as_
    return {"kind": "trigger", "when": {"event": "move", "subject": "self", "to": "bz"},
            "fort_e": fe, "effect": effect}


def _fe_static(races, mod, affects="self"):
    return {"kind": "static", "affects": affects, "fort_e": {"races": races}, "mod": mod}


def _power_lt_tapped():
    return {"power_le": {"sum": [{"power_of": {"ref": "tapped"}}, -1]}}


def _discard_all_hand(owner):
    var = "h_you" if owner == "you" else "h_opp"
    return [{"op": "choose", "select": {"zone": "hand", "owner": owner, "count": "all"}, "as": var},
            {"op": "move", "select": {"ref": var, "count": "all"},
             "to": "graveyard", "reason": "discard"}]


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
                 if u.get("need") != "fort_e"]
        if cid == "dm20-015":
            card["abilities"] += [
                _fe_trigger(["ドラゴン"], [
                    {"op": "modify",
                     "select": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"]},
                                "count": "all"},
                     "mod": {"power": 3000}, "duration": "end_of_turn"}]),
                _fe_trigger(["ヒューマノイド"], [
                    {"op": "destroy",
                     "select": {"zone": "bz", "owner": "any",
                                "filter": {"types": ["creature"], "power_le": 2000}, "count": "all"}}])]
        elif cid == "dm20-021":
            card["abilities"] += [
                _fe_trigger(["グレートメカオー"], [
                    {"op": "flip_up", "select": {"zone": "shield", "owner": "you", "count": 2}}])]
        elif cid == "dm20-024":
            card["abilities"] += [
                _fe_trigger(["リキッド・ピープル"], [
                    {"op": "repeat",
                     "times": {"count": {"zone": "bz", "owner": "you",
                                         "filter": {"types": ["creature"]}}},
                     "body": [{"op": "may", "player": "you",
                               "body": [{"op": "draw", "player": "you", "count": 1}]}]},
                    {"op": "repeat",
                     "times": {"count": {"zone": "bz", "owner": "opp",
                                         "filter": {"types": ["creature"]}}},
                     "body": [{"op": "may", "player": "opp",
                               "body": [{"op": "draw", "player": "opp", "count": 1}]}]}])]
        elif cid == "dm20-048":
            card["abilities"] += [
                _fe_trigger(["ブレイブ・スピリット"], [
                    {"op": "modify",
                     "select": {"zone": "bz", "owner": "you",
                                "filter": {"races": ["ティラノ・ドレイク"]}, "count": "all"},
                     "mod": {"grant": ["speed_attacker"], "require": ["attack"]},
                     "duration": "end_of_turn"}])]
        elif cid == "dm20-052":
            card["abilities"] += [
                _fe_trigger(["アーク・セラフィム"], [
                    {"op": "move",
                     "select": {"zone": "mana", "owner": "you",
                                "filter": {"name": "霊騎ザファル・バニキス"}, "count": 1},
                     "to": "bz", "reason": "put"}])]
        elif cid == "dm20-s03":
            # FE1: このターン、このクリーチャーがブレイクしたシールドの S・トリガーを相手は使えない。
            # ブレイクの置換（continue: true）で、宣言の前に割れたシールドへ strigger off の印を付ける。
            # FE2: cip でのシールドブレイク（wiki の「cipでのシールドブレイク効果」）。
            card["abilities"] += [
                _fe_trigger(["ブレイブ・スピリット"], [
                    {"op": "modify", "select": {"ref": "self"},
                     "mod": {"gain": [{"kind": "replace",
                                       "when": {"event": "break", "subject": "self"},
                                       "continue": True,
                                       "instead": [{"op": "strigger",
                                                    "select": {"ref": "shield"}, "mode": "off"}]}]},
                     "duration": "end_of_turn"}]),
                _fe_trigger(["ティラノ・ドレイク"], [
                    {"op": "break", "player": "opp", "count": 1}])]
        elif cid == "dm21-010":
            card["abilities"] += [
                _fe_trigger(["グランド・デビル"], [
                    {"op": "move",
                     "select": {"zone": "bz", "owner": "opp",
                                "filter": {"types": ["creature"], **_power_lt_tapped()},
                                "count": 1},
                     "to": "hand", "reason": "return"}], as_="tapped")]
        elif cid == "dm21-017":
            card["abilities"] += [
                _fe_trigger(["ティラノ・ドレイク"], [
                    {"op": "destroy",
                     "select": {"zone": "bz", "owner": "opp",
                                "filter": {"types": ["creature"], **_power_lt_tapped()},
                                "count": 1}}], as_="tapped")]
        elif cid == "dm22-040":
            card["abilities"] += [
                _fe_trigger(["ドラゴン"], [
                    {"op": "choose",
                     "select": {"zone": "deck", "owner": "you", "look": True, "count": "all"},
                     "as": "a"},
                    {"op": "may", "body": [
                        {"op": "move", "select": {"ref": "a", "count": 1},
                         "to": "hand", "reason": "draw"}]},
                    {"op": "shuffle"}])]
        elif cid == "dm24ex1-039":
            # 「このクリーチャーの能力を使う」形: fort_e の誘発そのものが全捨て。
            card["abilities"] += [
                _fe_trigger(["デスパペット"],
                            _discard_all_hand("you") + _discard_all_hand("opp"))]
        elif cid == "dmx12b-059":
            card["abilities"] += [
                _fe_trigger(["ワイルド・ベジーズ"], [
                    {"op": "may", "body": [
                        {"op": "move",
                         "select": {"zone": "graveyard", "owner": "you",
                                    "filter": {"types": ["creature"]}, "count": 1},
                         "to": "mana", "reason": "put"}]}]),
                _fe_trigger(["ドラゴン"], [
                    {"op": "may", "body": [
                        {"op": "move",
                         "select": {"zone": "mana", "owner": "you",
                                    "filter": {"types": ["creature"]}, "count": 1},
                         "to": "hand", "reason": "return"}]}])]
        elif cid == "promoy5-034":
            card["abilities"] += [
                _fe_trigger(["キカイヒーロー"], [
                    {"op": "draw", "player": "you", "count": 1}]),
                {"kind": "trigger", "when": {"event": "move", "subject": "self", "to": "bz"},
                 "fort_e": {"races": ["グレートメカオー"]},
                 "if": {"exists": {"zone": "hand", "owner": "you"}},
                 "effect": [{"op": "may", "body": [
                     {"op": "move", "select": {"zone": "hand", "owner": "you", "count": 1},
                      "to": "shield", "reason": "put"},
                     {"op": "move", "select": {"zone": "shield", "owner": "you", "count": 1},
                      "to": "hand", "reason": "put", "strigger": "off"}]}]}]
        elif cid == "sp-017":
            # partial の攻撃誘発 +4000 を、標準のパワーアタッカー形（常在型 power_when）に正す。
            card["abilities"] = [
                card["abilities"][0],
                _fe_static(["ブレイブ・スピリット"],
                           {"power_when": {"amount": 4000, "when": "attacking"}})]
        elif cid == "dm20-006":
            card["abilities"] += [
                _fe_trigger(["キカイヒーロー"], [
                    {"op": "tap",
                     "select": {"zone": "bz", "owner": "opp",
                                "filter": {"types": ["creature"], "power_le": 3000},
                                "count": 1}}]),
                _fe_trigger(["グレートメカオー"], [
                    {"op": "tap",
                     "select": {"zone": "bz", "owner": "opp",
                                "filter": {"types": ["creature"], "power_ge": 4000},
                                "count": 1}}])]
        elif cid == "dm20-009":
            you_mode = [
                {"op": "choose", "select": {"zone": "hand", "owner": "you", "count": "all"},
                 "as": "h"},
                {"op": "move", "select": {"ref": "h", "count": "all"}, "to": "deck", "reason": "put"},
                {"op": "shuffle"},
                {"op": "draw", "player": "you", "count": {"var": "h"}}]
            opp_mode = [
                {"op": "choose", "select": {"zone": "hand", "owner": "opp", "count": "all"},
                 "as": "h"},
                {"op": "move", "select": {"ref": "h", "count": "all"}, "to": "deck", "reason": "put"},
                {"op": "shuffle", "player": "opp"},
                {"op": "draw", "player": "opp", "count": {"var": "h"}}]
            card["abilities"] += [
                _fe_trigger(["ディープ・マリーン"], [
                    {"op": "move",
                     "select": {"zone": "bz", "owner": "any",
                                "filter": {"types": ["creature"]}, "count": 1},
                     "to": "hand", "reason": "return"}]),
                _fe_trigger(["グランド・デビル"], [
                    {"op": "modal", "modes": [you_mode, opp_mode]}])]
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
