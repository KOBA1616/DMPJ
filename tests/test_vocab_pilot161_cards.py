"""語彙パイロット第161弾: attacked_this_turn_condition の対象11件の検証（再変換ラウンド197で登録8件・差し戻し3件）。

登録8件は rejects の partial に履歴カウンタ条件の条項を足し、unsupported を
外したもの（converted の登録形で検証する）。差し戻し2件は unsupported の need を
絞り込んだもの（build で再構成して検証する）。
dm36-038 は rejects 行自体に名前・partial が無く（原文データ未収録）、
再提出できないため対象外（gap 名だけ attack_on_scoped_player_denial に絞り込んだ）。

変換の型:
- 攻撃できない形（常在型の if に turn_count の cmp、mod は deny 両方向）:
  dmrp14-089（owner: any, other）、dmrp14-s04（owner: you, other）、
  dmrp21-067（owner: any, other, filter 火）、dm26sd1-p008（owner: you,
  filter power_ge 12000、other なし＝自分も含む。ツインパクトのクリーチャー面）
- 条件つき誘引: dmr17-s09（partial にある must_be_attacked 常在型の if へ
  attack_on == 0 の cmp を追加）
- 呪文の条件形: dm25rp4-044（op if ＋ force_battle）、dm25rp4-048（op if ＋ may でマナ置き）
- ターン終わりの条件破壊: dmrp06-079（choose で選び、スレイヤー付与、
  delayed_trigger の効果に attack_by の cmp）
- 差し戻し: dmrp08-023（「2体以上」は攻撃したクリーチャーの distinct な数えが要る）、
  dm25ex3-020（「自分がカードを実行した時」の統合トリガーが無い）
"""
import copy
import json
from pathlib import Path

import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
CONVERTED = Path(__file__).parent.parent / "data" / "cards" / "converted.yaml"

DENY = ["attack_player", "attack_creature"]


def _deny_static(spec):
    return {"kind": "static", "affects": "self",
            "if": {"cmp": [{"turn_count": spec}, "==", 0]},
            "mod": {"deny": list(DENY)}}


def _attacked_any():
    return {"cmp": [{"turn_count": {"kind": "attack", "owner": "any"}}, ">=", 1]}


SPELL_079 = [
    {"op": "choose", "select": {"zone": "bz", "owner": "any", "filter": {"types": ["creature"]}, "count": 1}, "as": "t"},
    {"op": "modify", "select": {"ref": "t"}, "mod": {"grant": ["slayer"]}, "duration": "end_of_turn"},
    {"op": "delayed_trigger", "when": {"event": "turn_end"}, "effect": [
        {"op": "if", "cond": {"cmp": [{"turn_count": {"kind": "attack_by", "ref": "t"}}, ">=", 1]},
         "then": [{"op": "destroy", "select": {"ref": "t"}}]}]},
]

ADD_044 = {"op": "if", "cond": _attacked_any(), "then": [
    {"op": "may", "body": [
        {"op": "force_battle",
         "a": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"]}},
         "b": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}}}]}]}

ADD_048 = {"op": "if", "cond": _attacked_any(), "then": [
    {"op": "may", "body": [
        {"op": "move", "select": {"zone": "bz", "owner": "opp", "filter": {"cost_le": 5}, "count": 1},
         "to": "mana", "reason": "put"}]}]}

REGISTER = ["dmrp14-089", "dmrp14-s04", "dmrp21-067", "dm26sd1-p008",
            "dmr17-s09", "dmrp06-079", "dm25rp4-044", "dm25rp4-048"]
BOUNCE = {"dm25ex3-020": "card_executed_trigger"}

NOTES = {
    "dmrp14-089": "「このターン、他のクリーチャーが攻撃していなければ攻撃できない」は常在型の if に turn_count（attack, owner: any, other）の cmp を置く形（第161弾）",
    "dmrp14-s04": "「このターン中に自分の他のクリーチャーが攻撃していなければ攻撃できない」は常在型の if に turn_count（attack, owner: you, other）の cmp を置く形（第161弾）",
    "dmrp21-067": "「このターン、他の火のクリーチャーが攻撃していなければ攻撃できない」は常在型の if に turn_count（attack, owner: any, other, filter 火）の cmp を置く形（第161弾）",
    "dm26sd1-p008": "「このターン、自分のパワー12000以上のクリーチャーが攻撃していなければ攻撃できない」は常在型の if に turn_count（attack, owner: you, filter power_ge 12000）の cmp を置く形（第161弾）",
    "dmr17-s09": "「そのターンまだ攻撃されていなければ」は、partial にあった must_be_attacked 常在型の if へ turn_count（attack_on, ref: self）== 0 の cmp を追加して表現した（第161弾）",
    "dmrp06-079": "「選んだクリーチャーがこのターン中に攻撃していたら、ターンの終わりに破壊する」は delayed_trigger の効果に turn_count（attack_by, ref: 選択変数）の cmp を置く形（第161弾）",
    "dm25rp4-044": "「このターン、クリーチャーが攻撃していれば」は呪文の op if の cond に turn_count（attack, owner: any）の cmp を置く形（第161弾）。バトルは force_battle",
    "dm25rp4-048": "「このターン、クリーチャーが攻撃していれば」は呪文の op if の cond に turn_count（attack, owner: any）の cmp を置く形（第161弾）",
}


def _rows():
    return {r["id"]: r for r in (json.loads(line) for line in open(REJECTS, encoding="utf-8"))}


def build(cid, rows=None):
    """rejects の partial から提出形（登録または差し戻し）を作る。"""
    rows = rows if rows is not None else _rows()
    card = copy.deepcopy(rows[cid]["partial"])
    src = card.setdefault("source", {})
    if cid in BOUNCE:
        for u in src.get("unsupported", []):
            u["need"] = BOUNCE[cid]
        return card
    src.pop("unsupported", None)
    src["notes"] = f"再変換ラウンド197。第161弾の再変換。{NOTES[cid]}"
    src["review"] = "pending"
    if cid == "dmrp14-089":
        card["abilities"].append(_deny_static({"kind": "attack", "owner": "any", "other": True}))
    elif cid == "dmrp14-s04":
        card["abilities"].append(_deny_static({"kind": "attack", "owner": "you", "other": True}))
    elif cid == "dmrp21-067":
        card.setdefault("abilities", []).append(
            _deny_static({"kind": "attack", "owner": "any", "other": True, "filter": {"civs": ["fire"]}}))
    elif cid == "dm26sd1-p008":
        card["faces"][0]["abilities"].append(
            _deny_static({"kind": "attack", "owner": "you", "filter": {"power_ge": 12000}}))
    elif cid == "dmr17-s09":
        for ab in card["abilities"]:
            if ab.get("kind") == "static" and (ab.get("mod") or {}).get("must_be_attacked"):
                ab["if"]["all"].append({"cmp": [{"turn_count": {"kind": "attack_on", "ref": "self"}}, "==", 0]})
    elif cid == "dmrp06-079":
        card["spell"] = copy.deepcopy(SPELL_079)
    elif cid == "dm25rp4-044":
        card["spell"].append(copy.deepcopy(ADD_044))
    elif cid == "dm25rp4-048":
        card["spell"].append(copy.deepcopy(ADD_048))
    return card


def test_bounce_forms_parse():
    rows = _rows()
    for cid, need in BOUNCE.items():
        card = build(cid, rows)
        needs = [u["need"] for u in card["source"]["unsupported"]]
        assert needs == [need], (cid, needs)
        parse_card(card, TABLES)
    row36 = rows["dm36-038"]
    assert row36["gaps"] == ["attack_on_scoped_player_denial"]


def _deny_statics(card):
    return [a for a in (card.get("abilities") or [])
            if a.get("kind") == "static" and (a.get("mod") or {}).get("deny") == DENY]


def test_registered_forms():
    data = yaml.safe_load(CONVERTED.read_text(encoding="utf-8"))
    conv = {c["id"]: c for c in data["cards"]}
    for cid in REGISTER:
        assert cid in conv, f"{cid} が converted に無い"
        card = conv[cid]
        assert not (card.get("source") or {}).get("unsupported"), cid
        parse_card(card, TABLES)
    for cid in ("dmrp14-089", "dmrp14-s04", "dmrp21-067"):
        sts = _deny_statics(conv[cid])
        assert len(sts) == 1, cid
        spec = sts[0]["if"]["cmp"][0]["turn_count"]
        assert spec["kind"] == "attack" and spec.get("other") is True, (cid, spec)
    spec = _deny_statics(conv["dmrp14-089"])[0]["if"]["cmp"][0]["turn_count"]
    assert spec["owner"] == "any"
    spec = _deny_statics(conv["dmrp14-s04"])[0]["if"]["cmp"][0]["turn_count"]
    assert spec["owner"] == "you"
    spec = _deny_statics(conv["dmrp21-067"])[0]["if"]["cmp"][0]["turn_count"]
    assert spec["filter"] == {"civs": ["fire"]}
    face0 = conv["dm26sd1-p008"]["faces"][0]
    sts = [a for a in face0["abilities"] if a.get("kind") == "static" and (a.get("mod") or {}).get("deny") == DENY]
    assert len(sts) == 1
    spec = sts[0]["if"]["cmp"][0]["turn_count"]
    assert spec == {"kind": "attack", "owner": "you", "filter": {"power_ge": 12000}}, spec
    s09 = next(a for a in conv["dmr17-s09"]["abilities"]
               if a.get("kind") == "static" and (a.get("mod") or {}).get("must_be_attacked"))
    cmps = [c for c in s09["if"]["all"] if "cmp" in c]
    assert cmps == [{"cmp": [{"turn_count": {"kind": "attack_on", "ref": "self"}}, "==", 0]}], cmps
    assert conv["dmrp06-079"]["spell"] == SPELL_079
    assert ADD_044 in conv["dm25rp4-044"]["spell"]
    assert ADD_048 in conv["dm25rp4-048"]["spell"]
