"""第166弾 shield_force の再変換ラウンド202: 対象16件の生成と登録形の検証。

生成は rejects の partial に「出す時の選択（sforce_link 誘発）＋ sforce 印の
獲得能力」を足す決定的な変換。partial に印刷キーワードとして紛れていた獲得分
（dm28-046 の unblockable、dm28-096 の cannot_be_attacked）は印つき常在型へ移す。
dm26rp1-s001 / dm28-049 / dm31-s01 は残りの節が別語彙のため、解けた分を
partial に残して差し戻す（unsupported を差し替える）。
"""
import json
from pathlib import Path

import yaml

from dmsim.defs import load_tables, parse_card

ROOT = Path(__file__).parent.parent
BACKUP = Path.home() / "workspace/DMPJ-work/DMPJ-main.old-round201-20261110/data/cards/raw/rejects.jsonl"
TABLES = load_tables()

LINK = {"kind": "trigger", "when": {"event": "move", "subject": "self", "to": "bz"},
        "effect": [{"op": "sforce_link"}]}

TARGETS = ["28-sec001", "dm26rp1-s001", "dm28-026", "dm28-031", "dm28-032", "dm28-037",
           "dm28-046", "dm28-049", "dm28-075", "dm28-091", "dm28-096", "dm29-036",
           "dm31-s01", "dmbd18-se06", "dmex03-004", "dmc68-010"]
BOUNCED = {"dm26rp1-s001": "shield_hand_shieldize_trigger",
           "dm28-049": "draw_replacement_double",
           "dm31-s01": "g_castle"}
NOTES = "再変換ラウンド202。第166弾 shield_force の再変換。"


def _rows():
    out = {}
    for path in (ROOT / "data/cards/raw/rejects.jsonl", BACKUP):
        if not path.exists():
            continue
        for line in open(path):
            r = json.loads(line)
            out.setdefault(r["id"], r)
    return out


def _sf_static(mod, **kw):
    d = {"kind": "static", "sforce": True, "mod": mod}
    d.update(kw)
    return d


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
                 if u.get("need") != "shield_force"]
        if cid in ("28-sec001", "dmbd18-se06"):
            card["abilities"] += [LINK, _sf_static({"grant": ["blocker"]}),
                                  _sf_static({"no_leave": True})]
        elif cid == "dm28-031":
            card["abilities"] += [LINK, _sf_static({"power_when": {"amount": 6000, "when": "attacking"},
                                                    "grant": ["double_breaker"]})]
        elif cid == "dm28-032":
            card["abilities"] += [LINK, _sf_static({"power": 11000, "grant": ["double_breaker"]})]
        elif cid == "dm28-037":
            card["abilities"] += [LINK, _sf_static({"power": 3000, "grant": ["double_breaker"]})]
        elif cid == "dm28-091":
            card["abilities"] += [LINK, _sf_static({"power": 4000})]
        elif cid == "dm28-046":
            card["keywords"] = [k for k in card.get("keywords", []) if k != "unblockable"]
            card["abilities"] += [LINK, _sf_static({"grant": ["unblockable"]})]
        elif cid == "dm28-096":
            card["keywords"] = [k for k in card.get("keywords", []) if k != "cannot_be_attacked"]
            card["abilities"] += [LINK, _sf_static({"grant": ["cannot_be_attacked"]})]
        elif cid == "dm28-026":
            card["abilities"] += [LINK, {"kind": "trigger", "sforce": True,
                                         "when": {"event": "block", "subject": "self"},
                                         "effect": [{"op": "may", "body": [
                                             {"op": "move",
                                              "select": {"zone": "graveyard", "owner": "you",
                                                         "filter": {"types": ["creature"]}, "count": 1},
                                              "to": "hand", "reason": "return"}]}]}]
        elif cid == "dm28-075":
            card["abilities"] += [LINK, {"kind": "trigger", "sforce": True,
                                         "when": {"event": "turn_end"},
                                         "effect": [{"op": "untap",
                                                     "select": {"zone": "bz", "owner": "you",
                                                                "filter": {"types": ["creature"]}, "count": 1}}]}]
        elif cid == "dm29-036":
            card["abilities"] += [LINK, _sf_static({"add_races": ["ナイト"]},
                                                   affects={"zone": "bz", "owner": "you",
                                                            "filter": {"types": ["creature"]}})]
        elif cid == "dmex03-004":
            card["abilities"] += [LINK, {"kind": "trigger", "sforce": True,
                                         "when": {"event": "attack", "subject": "self"},
                                         "effect": [
                                             {"op": "move",
                                              "select": {"zone": "bz", "owner": "opp",
                                                         "filter": {"types": ["creature"]}, "count": "all"},
                                              "to": "deck", "reason": "put"},
                                             {"op": "shuffle", "player": "opp"}]}]
        elif cid == "dmc68-010":
            card["abilities"] += [LINK, _sf_static({"power": 5500, "grant": ["double_breaker"]})]
        elif cid == "dm26rp1-s001":
            card["abilities"] += [LINK, _sf_static({"no_leave": True},
                                                   affects={"zone": "bz", "owner": "you",
                                                            "filter": {"types": ["creature"]}})]
            unsup.append({"need": "shield_hand_shieldize_trigger",
                          "text": "このクリーチャーが攻撃またはブロックした時、カードを1枚引いてもよい。その後、自分のシールドを1つ手札に加えてもよい。その「S・トリガー」は使えない。その後、自分の手札を1枚、表向きまたは裏向きでシールド化してもよい。"})
        elif cid == "dm28-049":
            card["abilities"] += [LINK]
            unsup.append({"need": "draw_replacement_double",
                          "text": "自分がカードを引く時、かわりにその2倍の枚数のカードを引いてもよい。そうした場合、引いたカード2枚につき自分の手札を1枚、好きな順序で山札の一番下に置く。"})
        elif cid == "dm31-s01":
            card["types"] = ["creature", "evolution"]
            card["evolve_from"] = {"races": ["エンジェル・コマンド"]}
            card["abilities"] += [LINK, _sf_static({"cost": 4},
                                                   affects={"zone": "hand", "owner": "any",
                                                            "filter": {"types": ["creature"],
                                                                       "not_civs": ["light"]}})]
            unsup.append({"need": "g_castle",
                          "text": "自分のシールドゾーンにある城1枚につき、自分のクリーチャーの召喚コストを1少なくしてもよい。ただしコストは1より少なくならない。"})
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
        if cid == "28-sec001":
            # 同一カードの別刷り: dmbd18-se06 の登録に alias として含まれる
            assert "28-sec001" in (conv["dmbd18-se06"].get("source") or {}).get("aliases", [])
            continue
        assert cid in conv, cid
        card = parse_card(conv[cid], TABLES)
        assert any(a.get("sforce") for a in card.abilities), cid
        assert any(op.get("op") == "sforce_link"
                   for a in card.abilities for op in a.get("effect", [])), cid
