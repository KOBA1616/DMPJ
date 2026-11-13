"""語彙パイロット第163弾: reveal_until の対象の検証（再変換ラウンド199）。

登録形は rejects の partial に reveal_until の条項を足し（partial に無い能力は
全文から書き起こし）、unsupported を外したもの。converted の登録形で検証する。

変換の型:
- 基本形: reveal_until で as / rest_as に束縛し、後続の move / shuffle で行き先を決める。
- 動的な数: count: {var: 先に破壊・移動した変数}（dm26ex3-061、dmr13-020、dmx12b-020）。
- 相対条件: filter の式値 cost_le / power_le に cost_of / power_of（dmex17-053、dmr09-006、dmx22a-021）。
- 持ち主の山札: player_from（dmbd18-se07、dmex17-053、dmx22b-137）。相手の山札は player: opp
  （dmr09-006、dm25ex2-cho027）。
- 残りをシャッフルして山札の下: move の order: shuffle（dm23ex2-070）。
差し戻し2件: dmx22b-043（サイキックの区別が要る → psychic_filter。
GR・超次元・サイキック関連は実装しない方針のため、この区別は今回も見送る）、
dm24ex2-040（はじめて呪文を唱えた時の誘発＋その呪文基準の相対条件＋無料詠唱の
複合 → first_cast_spell_trigger）。
dm24ex2-chog03 は rejects 行に id / gaps / text しか無く（partial も名前も無い）、
reopen の対象にならないため手を付けない。
"""
import copy
import json
from pathlib import Path

import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
CONVERTED = Path(__file__).parent.parent / "data" / "cards" / "converted.yaml"

CRE = {"types": ["creature"]}


def _cip(effect):
    return {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"}, "effect": effect}


def _mv(ref, to, reason="put", **kw):
    d = {"op": "move", "select": {"ref": ref, "count": "all"}, "to": to, "reason": reason}
    d.update(kw)
    return d


REVEAL_DRAGON_PUT = [
    {"op": "destroy", "select": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"], "not_race_has": "ドラゴン"}, "count": "all"}, "as": "d"},
    {"op": "reveal_until", "filter": {"types": ["creature"], "race_has": "ドラゴン", "evolution": False}, "count": {"var": "d"}, "as": "hit", "rest_as": "rest"},
    _mv("hit", "bz"),
    _mv("rest", "graveyard"),
]

CIP_061 = _cip(copy.deepcopy(REVEAL_DRAGON_PUT))

CIP_KIRIX = _cip([
    {"op": "reveal_until", "filter": {"types": ["creature"], "races": ["ファイアー・バード"]}, "count": 3, "as": "hit"},
    _mv("hit", "bz"),
    {"op": "shuffle"},
])
STATIC_KIRIX = {"kind": "static", "affects": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"], "races": ["ファイアー・バード"]}},
                "mod": {"grant": ["speed_attacker", "unblockable"]}}

LEAVE_004 = {"kind": "trigger", "when": {"event": "move", "from": "bz", "subject": "self"}, "effect": [
    {"op": "reveal_until", "filter": dict(CRE), "as": "hit", "rest_as": "rest"},
    _mv("hit", "bz"),
    _mv("rest", "deck", position="bottom", order="choose"),
]}

CIP_SE07 = _cip([
    {"op": "choose", "select": {"zone": "bz", "owner": "any", "filter": dict(CRE), "count": 1, "exclude": {"ref": "self"}}, "as": "t"},
    {"op": "move", "select": {"ref": "t"}, "to": "deck", "reason": "put", "position": "bottom"},
    {"op": "reveal_until", "player_from": "t", "filter": {"types": ["creature"], "evolution": False}, "as": "hit", "rest_as": "rest"},
    _mv("hit", "bz"),
    _mv("rest", "deck", position="bottom", order="choose"),
])

SPELL_053 = [
    {"op": "choose", "select": {"zone": "bz", "owner": "any", "filter": dict(CRE), "count": 1}, "as": "t"},
    {"op": "destroy", "select": {"ref": "t"}, "as": "d"},
    {"op": "reveal_until", "player_from": "d", "filter": {"types": ["creature"], "cost_le": {"sum": [{"cost_of": {"ref": "d"}}, -1]}}, "as": "hit"},
    _mv("hit", "bz"),
    {"op": "shuffle", "player_from": "d"},
]

CIP_019 = _cip([
    {"op": "if", "cond": {"cmp": [{"count": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"], "races": ["サイバーロード"]}}}, ">=", 3]},
     "then": [{"op": "may", "body": [
         {"op": "destroy", "select": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"], "races": ["サイバーロード"]}, "count": 3}, "as": "d"},
         {"op": "reveal_until", "filter": {"types": ["creature"], "races": ["サイバー・コマンド"], "evolution": False}, "as": "hit", "rest_as": "rest"},
         _mv("hit", "bz"),
         _mv("rest", "graveyard"),
     ]}]},
])

CIP_006 = _cip([
    {"op": "may", "body": [
        {"op": "destroy", "select": {"zone": "bz", "owner": "opp", "filter": dict(CRE), "count": 1}, "as": "d"},
        {"op": "if", "cond": {"cmp": [{"count": {"ref": "d"}}, ">=", 1]}, "then": [
            {"op": "reveal_until", "player": "opp", "filter": {"types": ["creature"], "evolution": False, "cost_le": {"cost_of": {"ref": "d"}}}, "as": "hit"},
            _mv("hit", "bz"),
            {"op": "shuffle", "player": "opp"},
        ]},
    ]},
])

SPELL_020 = [
    {"op": "destroy", "select": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"], "races": ["リキッド・ピープル"]}, "count": "all"}, "as": "d"},
    {"op": "reveal_until", "filter": {"types": ["creature"], "races": ["クリスタル・コマンド・ドラゴン"], "evolution": False}, "count": {"var": "d"}, "as": "hit"},
    _mv("hit", "bz"),
    {"op": "shuffle"},
]

SPELL_12B020 = [
    {"op": "move", "select": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"], "races": ["ファイアー・バード"]}, "count": "all"},
     "to": "deck", "reason": "put", "position": "bottom", "order": "choose", "as": "put"},
    {"op": "reveal_until", "filter": {"types": ["creature"], "races": ["アーマード・ドラゴン"], "evolution": False}, "count": {"var": "put"}, "as": "hit", "rest_as": "rest"},
    _mv("hit", "bz"),
    _mv("rest", "graveyard"),
]

CIP_001 = _cip([
    {"op": "reveal_until", "filter": {"any_of": [{"not_types": ["creature"]}, {"types": ["creature"], "vanilla": False}]}, "as": "hit", "rest_as": "rest"},
    _mv("hit", "hand", reason="draw"),
    _mv("rest", "bz"),
])
STATIC_001 = {"kind": "static", "affects": {"zone": "bz", "owner": "you", "filter": {"name_has": "パーロック"}},
              "mod": {"grant": ["unblockable"]}}

SPELL_22A021 = [
    {"op": "reveal_until", "filter": dict(CRE), "as": "hit", "rest_as": "rest"},
    {"op": "if", "cond": {"exists": {"ref": "hit"}}, "then": [
        {"op": "destroy", "select": {"zone": "bz", "owner": "any", "filter": {"types": ["creature"], "power_le": {"sum": [{"power_of": {"ref": "hit"}}, -1]}}, "count": "all"}},
        _mv("hit", "graveyard"),
    ]},
    _mv("rest", "graveyard"),
]

SPELL_137 = [
    {"op": "choose", "select": {"zone": "bz", "owner": "any", "filter": dict(CRE), "count": 1}, "as": "t"},
    {"op": "destroy", "select": {"ref": "t"}, "as": "d"},
    {"op": "reveal_until", "player_from": "d", "filter": {"types": ["creature"], "evolution": False}, "as": "hit", "rest_as": "rest"},
    _mv("hit", "bz"),
    _mv("rest", "graveyard"),
]

CIP_067 = _cip([
    {"op": "reveal_until", "filter": {"types": ["creature"], "races": ["キング・コマンド・ドラゴン"]}, "as": "hit"},
    _mv("hit", "hand", reason="draw"),
    {"op": "shuffle"},
])
DESTROYED_067 = {"kind": "trigger", "when": {"event": "move", "from": "bz", "to": "graveyard", "reason": "destroy", "subject": "self"},
                 "effect": [{"op": "may", "body": [
                     {"op": "move", "select": {"zone": ["hand", "mana"], "owner": "you", "filter": {"race_has": "ドラゴン"}, "count": 1}, "to": "bz", "reason": "put"}]}]}

CIP_027 = _cip([
    {"op": "reveal_until", "player": "opp", "filter": {"types": ["creature"], "evolution": False}, "as": "hit", "rest_as": "rest"},
    _mv("hit", "bz"),
    _mv("rest", "deck", position="bottom", order="choose"),
])

SPELL_070 = [
    {"op": "may", "body": [
        {"op": "destroy", "select": {"zone": "bz", "owner": "you", "filter": {"types": ["cross_gear"]}, "count": 1}, "as": "d"},
        {"op": "if", "cond": {"cmp": [{"count": {"ref": "d"}}, ">=", 1]}, "then": [
            {"op": "reveal_until", "filter": {"types": ["cross_gear"], "evolution": False}, "as": "hit", "rest_as": "rest"},
            _mv("hit", "bz"),
            _mv("rest", "deck", position="bottom", order="shuffle"),
        ]},
    ]},
]

REGISTER = ["dm26ex3-061", "dm26ex4-030", "dm26ex4-sec008", "dm32-004", "dmbd18-se07",
            "dmex17-053", "dmr05-019", "dmr09-006", "dmr13-020", "dmx12b-020", "dmx15-001",
            "dmx22a-021", "dmx22b-137", "promoy11-067", "dm25ex2-cho027", "dm23ex2-070"]
BOUNCE = {"dmx22b-043": "psychic_filter", "dm24ex2-040": "first_cast_spell_trigger"}

NOTE = "第163弾の再変換。reveal_until（出るまで表向きにする）で表現した"


def _rows():
    return {r["id"]: r for r in (json.loads(line) for line in open(REJECTS, encoding="utf-8"))}


def build(cid, rows=None):
    rows = rows if rows is not None else _rows()
    card = copy.deepcopy(rows[cid]["partial"])
    src = card.setdefault("source", {})
    if cid in BOUNCE:
        src["unsupported"] = [{"need": BOUNCE[cid], "text": (src.get("unsupported") or [{}])[0].get("text", "")}]
        return card
    src.pop("unsupported", None)
    src["notes"] = f"再変換ラウンド199。{NOTE}"
    src["review"] = "pending"
    if cid == "dm26ex3-061":
        card["abilities"] = [copy.deepcopy(CIP_061)]
    elif cid in ("dm26ex4-030", "dm26ex4-sec008"):
        card["types"] = ["creature", "evolution"]
        card["evolve_from"] = {"types": ["creature"], "civs": ["water", "fire"]}
        card["abilities"] = [copy.deepcopy(CIP_KIRIX), copy.deepcopy(STATIC_KIRIX)]
    elif cid == "dm32-004":
        card["types"] = ["creature", "evolution"]
        card["evolve_from"] = {"race_has": "サイバー"}
        card["abilities"] = [copy.deepcopy(LEAVE_004)]
    elif cid == "dmbd18-se07":
        card["abilities"].append(copy.deepcopy(CIP_SE07))
    elif cid == "dmex17-053":
        card["spell"] = copy.deepcopy(SPELL_053)
    elif cid == "dmr05-019":
        card["abilities"] = [copy.deepcopy(CIP_019)]
    elif cid == "dmr09-006":
        card["abilities"] = [copy.deepcopy(CIP_006)]
    elif cid == "dmr13-020":
        card["spell"] = copy.deepcopy(SPELL_020)
    elif cid == "dmx12b-020":
        card["spell"] = copy.deepcopy(SPELL_12B020)
    elif cid == "dmx15-001":
        card["abilities"] = [copy.deepcopy(CIP_001), copy.deepcopy(STATIC_001)]
    elif cid == "dmx22a-021":
        card["spell"] = copy.deepcopy(SPELL_22A021)
    elif cid == "dmx22b-137":
        card["spell"] = copy.deepcopy(SPELL_137)
    elif cid == "promoy11-067":
        card["abilities"] = [copy.deepcopy(CIP_067), copy.deepcopy(DESTROYED_067)]
    elif cid == "dm25ex2-cho027":
        card["abilities"] = [copy.deepcopy(CIP_027)]
    elif cid == "dm23ex2-070":
        card["spell"] = copy.deepcopy(SPELL_070)
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
    assert conv["dm26ex3-061"]["abilities"] == [CIP_061]
    assert conv["dmex17-053"]["spell"] == SPELL_053
    assert conv["dmr13-020"]["spell"] == SPELL_020
    assert conv["dmx12b-020"]["spell"] == SPELL_12B020
    assert conv["dmx22a-021"]["spell"] == SPELL_22A021
    assert conv["dmx22b-137"]["spell"] == SPELL_137
    assert conv["dm23ex2-070"]["spell"] == SPELL_070
    for cid in ("dm26ex4-030", "dm26ex4-sec008"):
        assert conv[cid]["abilities"] == [CIP_KIRIX, STATIC_KIRIX]
        assert conv[cid]["evolve_from"] == {"types": ["creature"], "civs": ["water", "fire"]}
    assert conv["dm32-004"]["abilities"] == [LEAVE_004]
    assert CIP_SE07 in conv["dmbd18-se07"]["abilities"]
    assert conv["dmr05-019"]["abilities"] == [CIP_019]
    assert conv["dmr09-006"]["abilities"] == [CIP_006]
    assert conv["dmx15-001"]["abilities"] == [CIP_001, STATIC_001]
    assert conv["promoy11-067"]["abilities"] == [CIP_067, DESTROYED_067]
    assert conv["dm25ex2-cho027"]["abilities"] == [CIP_027]
