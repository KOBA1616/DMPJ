"""語彙パイロット第162弾: extremal_power_selection の対象10件の検証（再変換ラウンド198で全件登録）。

登録形は rejects の partial に extremal セレクタの条項を足し（partial に無い
能力は全文から書き起こし）、unsupported を外したもの。converted の登録形で検証する。

変換の型:
- 選んで破壊/戻す/マナ置き: select に extremal: min_power / max_power。
  「相手は自身の〜を1体選ぶ」は chooser: opp（dm24bd4-010、dm25ex3-td14、
  dm25ex3-rp4011、dm23sp1-007）。「自分が選ぶ」は既定の chooser: you（dm31-046）。
- すべて: count: all（dm26sd1-w002f、dm25ex3-sp5 のモード1）。
- タップしている中で最小＋凍結: dm32-014（proto T297 と同型）。
- 2体選んでバトル: dm32-064（extremal の choose を exclude でつなぐ）。
- 条件つき S・トリガー付与: dm25ex3-sp5（zone: shield の self 常在型、
  dmx23-031 と同型。条件は cost_ge に sum 式で「マナ枚数より大きい」）。
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


def _sel(owner, extremal, count=1, chooser=None, **kw):
    s = {"zone": "bz", "owner": owner, "filter": {**CRE, **kw}, "extremal": extremal, "count": count}
    if chooser:
        s["chooser"] = chooser
    return s


def _cip(effect, **kw):
    t = {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"}, "effect": effect}
    t.update(kw)
    return t


SPELL_010 = [
    {"op": "destroy", "select": _sel("opp", "min_power", chooser="opp")},
    {"op": "move", "select": _sel("opp", "max_power", chooser="opp"), "to": "hand", "reason": "return"},
    {"op": "tap", "select": {"zone": "bz", "owner": "opp", "filter": dict(CRE), "count": "all"}},
]

ABILITIES_024 = [
    _cip([{"op": "destroy", "select": {"zone": "bz", "owner": "opp",
                                       "filter": {"types": ["creature"], "power_le": 3000}, "count": "all"}}]),
    {"kind": "trigger", "when": {"event": "attack", "subject": {"owner": "opp", "filter": dict(CRE)}},
     "effect": [{"op": "destroy", "select": _sel("opp", "min_power", chooser="opp", tapped=False)}]},
]

SPELL_RP4011 = [{"op": "modal", "count": 1, "modes": [
    [{"op": "move", "select": _sel("opp", "min_power", chooser="opp"), "to": "mana", "reason": "put"},
     {"op": "destroy", "select": _sel("opp", "max_power", chooser="opp")}],
    [{"op": "choose", "select": {"zone": "deck", "owner": "you", "from_top": 4, "look": True, "count": "all"}, "as": "a"},
     {"op": "move", "select": {"ref": "a", "count": 2}, "to": "mana", "reason": "put"},
     {"op": "move", "select": {"ref": "a", "count": "all"}, "to": "graveyard", "reason": "put"}],
]}]

STATIC_SP5 = {"kind": "static", "zone": "shield", "affects": "self",
              "if": {"exists": {"zone": "bz", "owner": "opp",
                                "filter": {"cost_ge": {"sum": [{"count": {"zone": "mana", "owner": "opp"}}, 1]}}}},
              "mod": {"grant": ["s_trigger"]}}

SPELL_SP5 = [{"op": "modal", "count": 2, "repeat": True, "modes": [
    [{"op": "move", "select": _sel("opp", "min_power", count="all"), "to": "mana", "reason": "put"}],
    [{"op": "choose", "select": {"zone": "deck", "owner": "you", "from_top": 2, "look": True, "count": "all"}, "as": "a"},
     {"op": "move", "select": {"ref": "a", "count": 1}, "to": "shield", "reason": "put"},
     {"op": "move", "select": {"ref": "a", "count": "all"}, "to": "mana", "reason": "put"}],
    [{"op": "move", "select": {"zone": "hand", "owner": "you", "filter": {"cost_le": 5, "not_types": ["spell"]}, "count": 1},
      "to": "bz", "reason": "put", "as": "e"},
     {"op": "modify", "select": {"ref": "e"}, "mod": {"grant": ["blocker"]}, "duration": "until_next_own_turn_start"}],
]}]

CIP_TD14 = _cip([{"op": "modal", "count": 1, "modes": [
    [{"op": "destroy", "select": _sel("opp", "min_power", chooser="opp")}],
    [{"op": "move", "select": {"zone": "bz", "owner": "opp", "filter": dict(CRE), "count": 1},
      "to": "hand", "reason": "return"}],
]}])

SPELL_046 = [{"op": "destroy", "select": _sel("opp", "min_power")}]

ABILITIES_014 = [_cip([
    {"op": "choose", "select": _sel("opp", "min_power", tapped=True), "as": "t"},
    {"op": "tap", "select": {"ref": "t"}, "no_untap_next": True},
])]

SPELL_064 = [
    {"op": "choose", "select": _sel("any", "max_power"), "as": "a"},
    {"op": "choose", "select": {**_sel("any", "max_power"), "exclude": {"ref": "a"}}, "as": "b"},
    {"op": "force_battle", "a": {"ref": "a"}, "b": {"ref": "b"}},
]

CIVIL_COUNT = {"cmp": [{"sum": [
    {"count": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"], "civs": ["darkness"]}}},
    {"count": {"zone": "bz", "owner": "you", "filter": {"types": ["tamaseed"], "civs": ["darkness"]}}},
]}, ">=", 3]}

CIPS_007 = [
    _cip([{"op": "destroy", "select": _sel("opp", "min_power", chooser="opp")}]),
    _cip([{"op": "destroy", "select": _sel("opp", "max_power", chooser="opp")}], **{"if": CIVIL_COUNT}),
]

CIP_W002F = _cip([{"op": "destroy", "select": _sel("opp", "max_power", count="all")}])

REGISTER = ["dm24bd4-010", "dm24ex3-024", "dm25ex3-rp4011", "dm25ex3-sp5", "dm25ex3-td14",
            "dm31-046", "dm32-014", "dm32-064", "dm23sp1-007", "dm26sd1-w002f"]

NOTE = "第162弾の再変換。extremal セレクタ（min_power / max_power）で表現した"


def _rows():
    return {r["id"]: r for r in (json.loads(line) for line in open(REJECTS, encoding="utf-8"))}


def build(cid, rows=None):
    rows = rows if rows is not None else _rows()
    card = copy.deepcopy(rows[cid]["partial"])
    src = card.setdefault("source", {})
    src.pop("unsupported", None)
    src["notes"] = f"再変換ラウンド198。{NOTE}"
    src["review"] = "pending"
    if cid == "dm24bd4-010":
        card["spell"] = copy.deepcopy(SPELL_010)
    elif cid == "dm24ex3-024":
        card["abilities"] = copy.deepcopy(ABILITIES_024)
    elif cid == "dm25ex3-rp4011":
        card["spell"] = copy.deepcopy(SPELL_RP4011)
    elif cid == "dm25ex3-sp5":
        card["text"] = rows[cid]["text"]   # partial の text は断片のため原文に戻す
        card["abilities"] = [copy.deepcopy(STATIC_SP5)]
        card["spell"] = copy.deepcopy(SPELL_SP5)
    elif cid == "dm25ex3-td14":
        card["abilities"].append(copy.deepcopy(CIP_TD14))
    elif cid == "dm31-046":
        card["spell"] = copy.deepcopy(SPELL_046)
    elif cid == "dm32-014":
        card["abilities"] = copy.deepcopy(ABILITIES_014)
    elif cid == "dm32-064":
        card["spell"] = copy.deepcopy(SPELL_064)
    elif cid == "dm23sp1-007":
        card["abilities"] = copy.deepcopy(CIPS_007) + card.get("abilities", [])
    elif cid == "dm26sd1-w002f":
        card["abilities"].append(copy.deepcopy(CIP_W002F))
    return card


def test_build_forms_parse():
    """提出形の再構成（rejects に残る multi-gap の同型カードにも使える形の確認）。"""
    rows = _rows()
    for cid in REGISTER:
        if cid not in rows:
            continue   # 登録済みで rejects から消えたものは test_registered_forms で検証
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
    assert conv["dm24bd4-010"]["spell"] == SPELL_010
    assert conv["dm31-046"]["spell"] == SPELL_046
    assert conv["dm32-064"]["spell"] == SPELL_064
    assert conv["dm25ex3-rp4011"]["spell"] == SPELL_RP4011
    assert conv["dm25ex3-sp5"]["spell"] == SPELL_SP5
    assert conv["dm25ex3-sp5"]["abilities"] == [STATIC_SP5]
    assert CIP_TD14 in conv["dm25ex3-td14"]["abilities"]
    assert CIP_W002F in conv["dm26sd1-w002f"]["abilities"]
    for ab in CIPS_007:
        assert ab in conv["dm23sp1-007"]["abilities"]
    assert conv["dm32-014"]["abilities"] == ABILITIES_014
    assert conv["dm24ex3-024"]["abilities"] == ABILITIES_024
