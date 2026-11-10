"""語彙パイロット第165弾: ura_ninja_strike の対象の検証（再変換ラウンド201）。

登録形は rejects の partial にウラ・ニンジャ・ストライクの declare 2本
（攻撃時／ブロック時。if = マナ枚数以上＋指定文明がマナにあること）と、
partial に欠けていた残りの能力を足し、unsupported を外したもの。
converted の登録形で検証する。

差し戻し2件: dm26ex4-010 / dm26ex4-sec007 切札混成 光隼 蒼斬丸
→ attack_cancel（「攻撃を中止する」が未実装。ウラ declare と出た時の
ドローは partial に入れたので、残りは中止条項のみ）。
"""
import copy
import json
from pathlib import Path

import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
CONVERTED = Path(__file__).parent.parent / "data" / "cards" / "converted.yaml"

CRE = {"types": ["creature"]}


def ura_declares(n, civs):
    conds = [{"cmp": [{"count": {"zone": "mana", "owner": "you"}}, ">=", n]}]
    conds += [{"exists": {"zone": "mana", "owner": "you", "filter": {"civs": [c]}}} for c in civs]
    if_ = conds[0] if len(conds) == 1 else {"all": conds}
    body = [{"op": "play_free", "select": {"ref": "self"}, "as": "ninja"},
            {"op": "delayed_trigger", "when": {"event": "turn_end"},
             "effect": [{"op": "move", "select": {"ref": "ninja"}, "to": "deck", "reason": "put", "position": "bottom"}]}]
    return [{"kind": "declare", "zone": "hand", "when": {"event": ev, "subject": {"owner": "opp"}},
             "if": copy.deepcopy(if_), "effect": copy.deepcopy(body)}
            for ev in ("attack", "block")]


def cip(effect):
    return {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"}, "effect": effect}


TRIG_045 = {"kind": "trigger", "when": {"event": "break", "player": "you"},
            "effect": [{"op": "destroy", "select": {"zone": "bz", "owner": "opp", "chooser": "opp",
                                                    "filter": {"types": ["creature"], "tapped": False}, "count": 1}}]}

CIP_057 = cip([{"op": "draw", "count": 2},
               {"op": "move", "select": {"zone": "hand", "owner": "you", "count": 1},
                "to": "graveyard", "reason": "discard", "as": "d"},
               {"op": "modify", "select": {"zone": "bz", "owner": "opp",
                                           "filter": {"types": ["creature"],
                                                      "cost_le": {"cost_of": {"ref": "d"}}, "cost_ge": {"cost_of": {"ref": "d"}}},
                                           "count": "all"},
                "mod": {"deny": ["attack_player", "attack_creature", "block"]},
                "duration": "until_next_own_turn_start"}])

CIP_062 = cip([{"op": "destroy", "select": {"zone": "bz", "owner": "any", "filter": {"cost_le": 2}, "count": "all"}}])

CIP_072 = cip([{"op": "move", "select": {"zone": "deck", "owner": "you", "from_top": 1},
                "to": "shield", "reason": "put"}])

CIP_084 = cip([{"op": "modify", "select": {"zone": "bz", "owner": "any", "filter": dict(CRE), "count": 1},
                "mod": {"power": 4000, "deny": ["attack_player"]}, "duration": "end_of_turn"}])

CIP_SEC3 = cip([{"op": "choose", "select": {"zone": "hand", "owner": "you", "filter": {"races": ["シノビ"]}, "count": "any"},
                 "as": "shown"},
                {"op": "modify", "select": {"zone": "bz", "owner": "opp", "filter": dict(CRE), "count": "all"},
                 "mod": {"power": {"amount": -1000, "count": {"ref": "shown"}}}, "duration": "end_of_turn"},
                {"op": "modify", "select": {"zone": "bz", "owner": "opp", "filter": dict(CRE), "count": "all"},
                 "mod": {"power": {"amount": -1000, "count": {"zone": "bz", "owner": "you", "filter": {"races": ["シノビ"]}}}},
                 "duration": "end_of_turn"}])

CIP_049 = cip([{"op": "draw", "count": 3},
               {"op": "choose", "select": {"zone": "hand", "owner": "you", "count": 2, "up_to": True}, "as": "top"},
               {"op": "move", "select": {"ref": "top"}, "to": "deck", "reason": "put", "position": "top", "order": "choose"},
               {"op": "choose", "select": {"zone": "hand", "owner": "you",
                                           "count": {"sum": [2, {"mul": [-1, {"var": "top"}]}]}}, "as": "bottom"},
               {"op": "move", "select": {"ref": "bottom"}, "to": "deck", "reason": "put", "position": "bottom", "order": "choose"}])

CIP_010 = cip([{"op": "repeat", "times": 2, "body": [{"op": "may", "body": [{"op": "draw", "count": 1}]}]}])

TRIGS_020 = [{"kind": "trigger", "when": {"event": "move", "from": "shield", "to": to, "subject": {"owner": "you"}},
              "effect": [{"op": "may", "body": [
                  {"op": "move", "select": {"ref": "subject"}, "to": "mana", "reason": "charge"}]}]}
             for to in ("hand", "graveyard")]

CIP_029 = cip([{"op": "move", "select": {"zone": "bz", "owner": "opp",
                                          "filter": {"cost_ge": {"sum": [{"count": {"zone": "mana", "owner": "opp"}}, 1]}}, "count": 1},
                "to": "deck", "reason": "put", "position": "bottom"}])

CIP_037 = cip([{"op": "choose", "select": {"zone": "bz", "owner": "you", "filter": dict(CRE), "count": 1}, "as": "t"},
               {"op": "modify", "select": {"ref": "t"}, "mod": {"grant": ["slayer"]}, "duration": "end_of_turn"},
               {"op": "delayed_trigger", "when": {"event": "move", "from": "bz", "to": "graveyard",
                                                  "reason": "destroy", "subject": {"ref": "t"}},
                "effect": [{"op": "draw", "count": 2}]}])

CIP_041 = cip([{"op": "destroy", "select": {"zone": "bz", "owner": "opp", "count": 1,
                                            "filter": {"types": ["creature"],
                                                       "any_of": [{"keyword": "blocker"}, {"power_le": 2000}]}}}])

SPEC = {   # id: (N, civs, 追加能力の並び [partial の能力より前に入れるもの])
    "dm25ex1-045": (3, ["darkness"], [TRIG_045]),
    "dm25ex1-057": (3, ["water"], [CIP_057]),
    "dm25ex1-062": (3, ["fire"], [CIP_062]),
    "dm25ex1-072": (5, ["light"], [CIP_072]),
    "dm25ex1-073": (3, ["light"], []),
    "dm25ex1-084": (3, ["nature"], [CIP_084]),
    "dm25ex1-secchosp3": (5, ["darkness"], [CIP_SEC3]),
    "dm26ex3-049": (6, ["water"], [CIP_049]),
    "dm26ex4-cho042": (3, ["water"], [CIP_057]),
    "dm26rp1-020": (2, ["nature"], TRIGS_020),
    "dm26rp1-029": (4, ["light"], [CIP_029]),
    "dm26rp1-033": (4, ["water"], []),
    "dm26rp1-037": (2, ["darkness"], [CIP_037]),
    "dm26rp1-041": (3, ["fire"], [CIP_041]),
}
REGISTER = list(SPEC)
BOUNCE = {"dm26ex4-010": "attack_cancel", "dm26ex4-sec007": "attack_cancel"}
BOUNCE_SPEC = (6, ["light", "water"], [CIP_010])

NOTE = "第165弾の再変換。ウラ・ニンジャ・ストライクを declare 2本（マナ枚数＋指定文明の条件）で表現した"


def _rows():
    return {r["id"]: r for r in (json.loads(line) for line in open(REJECTS, encoding="utf-8"))}


def build(cid, rows=None):
    rows = rows if rows is not None else _rows()
    card = copy.deepcopy(rows[cid]["partial"])
    src = card.setdefault("source", {})
    if cid in BOUNCE:
        n, civs, extra = BOUNCE_SPEC
        card["abilities"] = ura_declares(n, civs) + copy.deepcopy(extra) + list(card.get("abilities") or [])
        src["unsupported"] = [{"need": BOUNCE[cid],
                               "text": "各ターンに1度、相手のクリーチャーが攻撃する時、自分の手札を1枚捨ててもよい。そうしたら、攻撃を中止する。"}]
        return card
    n, civs, extra = SPEC[cid]
    src.pop("unsupported", None)
    src["notes"] = f"再変換ラウンド201。{NOTE}"
    src["review"] = "pending"
    card["abilities"] = ura_declares(n, civs) + copy.deepcopy(extra) + list(card.get("abilities") or [])
    return card


def test_build_forms_parse():
    """提出形の再構成（登録済みで rejects から消えたものは test_registered_forms で検証）。"""
    rows = _rows()
    for cid in REGISTER:
        if cid not in rows:
            continue
        card = build(cid, rows)
        assert not (card.get("source") or {}).get("unsupported"), cid
        parse_card(card, TABLES)


def test_registered_forms():
    data = yaml.safe_load(CONVERTED.read_text(encoding="utf-8"))
    conv = {c["id"]: c for c in data["cards"]}
    for cid in REGISTER:
        assert cid in conv, f"{cid} が converted に無い"
        card = conv[cid]
        assert not (card.get("source") or {}).get("unsupported"), cid
        parse_card(card, TABLES)
        n, civs, extra = SPEC[cid]
        decls = [a for a in card["abilities"] if a["kind"] == "declare"]
        assert decls == ura_declares(n, civs), cid
        for ab in extra:
            assert ab in card["abilities"], cid
