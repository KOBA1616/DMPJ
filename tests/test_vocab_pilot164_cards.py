"""語彙パイロット第164弾: chosen_protection_scoped の対象の検証（再変換ラウンド200）。

登録形は rejects の partial に範囲つき deny の条項を足し、unsupported を外したもの。
converted の登録形で検証する。範囲は deny の辞書形 {action: be_chosen, other: 発生源フィルタ}:

- A 呪文からだけ: other {types: [spell]}
- B コスト4以下の呪文から: other {types: [spell], cost_le: 4}
- D 多色ではないクリーチャーの能力または呪文から: other {any_of: [creature, spell], multicolor: false}
- E 自分以下のコストのカードから: other {cost_le: {cost_of: {ref: self}}}
  （other フィルタの式は保護される側を self として評価される。第126弾）

差し戻し1件: dm15-022 聖騎士ウラヌス → crossed_gear_chosen_protection
（保護の対象が「このクリーチャーにクロスしてあるクロスギア」で、常在型の
affects では指せない。逆向きの affects: crossed はギア側からホストを指す形）。
"""
import copy
import json
from pathlib import Path

import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
CONVERTED = Path(__file__).parent.parent / "data" / "cards" / "converted.yaml"

A = {"action": "be_chosen", "other": {"types": ["spell"]}}
B = {"action": "be_chosen", "other": {"types": ["spell"], "cost_le": 4}}
D = {"action": "be_chosen", "other": {"any_of": [{"types": ["creature"]}, {"types": ["spell"]}], "multicolor": False}}
E = {"action": "be_chosen", "other": {"cost_le": {"cost_of": {"ref": "self"}}}}

CRE = {"types": ["creature"]}


def _self_static(deny):
    return {"kind": "static", "affects": "self", "mod": {"deny": [copy.deepcopy(deny)]}}


STATIC_FIONA = {"kind": "static",
                "affects": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"], "races": ["ドリームメイト"]}, "other": True},
                "mod": {"deny": ["be_chosen"]}}
CIP_FIONA = {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "may", "body": [
                 {"op": "move", "select": {"zone": "mana", "owner": "you", "filter": {"types": ["field"]}, "count": 1},
                  "to": "bz", "reason": "put"}]}]}

STATIC_018 = {"kind": "static",
              "affects": {"zone": "bz", "owner": "you",
                          "filter": {"any_of": [{"name_has": "禁断"}, {"races": ["ソニック・コマンド"]}, {"races": ["イニシャルズ"]}]}},
              "mod": {"deny": [B]}}

TRIG_035 = {"kind": "trigger", "when": {"event": "move", "from": "bz", "to": "graveyard", "reason": "destroy", "subject": "self"},
            "effect": [{"op": "modify", "select": {"zone": "bz", "owner": "you", "filter": dict(CRE), "count": 1},
                        "mod": {"deny": [A]}, "duration": "until_next_own_turn_start"}]}

TRIG_BD3 = {"kind": "trigger", "when": {"event": "attack", "subject": "self"},
            "effect": [{"op": "modify", "select": {"ref": "self"}, "mod": {"deny": [B]}, "duration": "during_attack"}]}

STATIC_050 = {"kind": "static", "affects": {"zone": "bz", "owner": "you", "filter": {"race_has": "ドラゴン"}},
              "if": {"hyper": True}, "mod": {"deny": [A]}}

STATIC_063 = {"kind": "static", "choukon": True, "affects": "self", "mod": {"deny": [E]}}

STATIC_010 = {"kind": "static", "affects": "crossed", "mod": {"deny": [A]}}

STATIC_015 = {"kind": "static", "affects": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"], "civs": ["water"]}},
              "if": {"cmp": [{"count": {"zone": "shield", "owner": "opp"}}, "<=", 2]}, "mod": {"deny": [A]}}

STATIC_S02 = {"kind": "static", "affects": {"zone": "bz", "owner": "you", "filter": dict(CRE)},
              "if": {"exists": {"zone": "bz", "owner": "you", "filter": {"types": ["d2_field"]}}}, "mod": {"deny": [A]}}

REGISTER = ["dm25ex4-018", "dm26rp3-035", "dm26rp3-sec019", "dmsp02-011",
            "dm25ex2-chog02", "dm22ex1-099", "dm23bd6-020", "dmrp07-004", "dm24bd3-007",
            "dm26ex3-050", "dm25rp4-063", "dm28-010", "dmr18-015", "dmr21-s02"]
BOUNCE = {"dm15-022": "crossed_gear_chosen_protection"}
TWINPACTS = ("dm22ex1-099", "dm23bd6-020", "dmrp07-004")

NOTE = "第164弾の再変換。範囲つきの「選ばれない」を deny の辞書形（発生源フィルタ）で表現した"


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
    src["notes"] = f"再変換ラウンド200。{NOTE}"
    src["review"] = "pending"
    if cid == "dm24ex3-rp3tr6":
        card["abilities"] = [copy.deepcopy(CIP_FIONA), copy.deepcopy(STATIC_FIONA)]
    elif cid == "dm25ex4-018":
        card["abilities"].append(copy.deepcopy(STATIC_018))
    elif cid in ("dm26rp3-035", "dm26rp3-sec019"):
        card["abilities"].append(copy.deepcopy(TRIG_035))
    elif cid == "dmsp02-011":
        card["abilities"].append(_self_static(B))
    elif cid == "dm25ex2-chog02":
        card["abilities"].append(_self_static(D))
    elif cid in TWINPACTS:
        face = card["faces"][0]
        face.setdefault("abilities", []).append(_self_static(A))
    elif cid == "dm24bd3-007":
        card["abilities"].append(copy.deepcopy(TRIG_BD3))
    elif cid == "dm26ex3-050":
        card["abilities"].append(copy.deepcopy(STATIC_050))
    elif cid == "dm25rp4-063":
        card["abilities"] = [copy.deepcopy(STATIC_063)]
    elif cid == "dm28-010":
        card["abilities"].append(copy.deepcopy(STATIC_010))
    elif cid == "dmr18-015":
        card["abilities"].append(copy.deepcopy(STATIC_015))
    elif cid == "dmr21-s02":
        card["abilities"].append(copy.deepcopy(STATIC_S02))
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
    # dm24ex3-rp3tr6 フィオナは real_akashic.yaml に手書き変換が既にあり（同じ2能力）、
    # rejects の行は古い残りだった。converted へは登録せず、行だけを掃除した
    assert "dm24ex3-rp3tr6" not in rows
    akashic = yaml.safe_load((CONVERTED.parent / "real_akashic.yaml").read_text(encoding="utf-8"))
    fiona = next(c for c in akashic["cards"] if c["id"] == "dm24ex3-rp3tr6")
    parse_card(fiona, TABLES)
    assert fiona["abilities"][0] == CIP_FIONA
    st = fiona["abilities"][1]
    assert st["mod"] == {"deny": ["be_chosen"]} and st["affects"].get("other") is True


def test_registered_forms():
    data = yaml.safe_load(CONVERTED.read_text(encoding="utf-8"))
    conv = {c["id"]: c for c in data["cards"]}
    for cid in REGISTER:
        assert cid in conv, f"{cid} が converted に無い"
        card = conv[cid]
        assert not (card.get("source") or {}).get("unsupported"), cid
        parse_card(card, TABLES)
    assert "dm24ex3-rp3tr6" not in conv   # 手書き変換（real_akashic.yaml）が正本
    assert STATIC_018 in conv["dm25ex4-018"]["abilities"]
    for cid in ("dm26rp3-035", "dm26rp3-sec019"):
        assert TRIG_035 in conv[cid]["abilities"]
    assert _self_static(B) in conv["dmsp02-011"]["abilities"]
    assert _self_static(D) in conv["dm25ex2-chog02"]["abilities"]
    for cid in TWINPACTS:
        assert _self_static(A) in conv[cid]["faces"][0]["abilities"]
    assert TRIG_BD3 in conv["dm24bd3-007"]["abilities"]
    assert STATIC_050 in conv["dm26ex3-050"]["abilities"]
    assert conv["dm25rp4-063"]["abilities"] == [STATIC_063]
    assert STATIC_010 in conv["dm28-010"]["abilities"]
    assert STATIC_015 in conv["dmr18-015"]["abilities"]
    assert STATIC_S02 in conv["dmr21-s02"]["abilities"]
