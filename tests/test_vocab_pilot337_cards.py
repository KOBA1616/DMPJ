"""語彙パイロット第337弾の対象カード（実カード parse）。

対象は pure な evolution_base_from_graveyard 3件（未登録、
rejects 残存）:
- dm25rp1-018 至高の邪騎 スベルニル（partial はキーワードのみ。
  本弾で choose＋move {stack_evo} を構成。partial の source に
  aliases [dm25rp1-sec17, promoy24-020]）
- dm25rp2-sp3 魔光神官ルドルフ・アルカディア（partial は
  キーワードのみ。本弾で may 切削＋choose＋move を構成。
  aliases 5件）
- dm25ex1-069 神滅翔天ポッポ・ジュヴィラ（partial は能力なし。
  本弾で grave_evo 宣言を構成。aliases 3件）

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
_conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import all_cards, proto_card  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402

TABLES = load_tables()
ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"

MOVE_STACK = {"op": "move", "select": {"ref": "p", "count": "all"},
              "to": "bz", "reason": "put", "stack_evo": True,
              "evo_source": {"ref": "self"}}

FORM_018 = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "may", "body": [
        {"op": "choose",
         "select": {"zone": "graveyard", "owner": "you",
                    "filter": {"types": ["creature"], "cost_le": 5,
                               "any_of": [{"neo": True},
                                          {"evolution": True}],
                               "evolves_from": "self"},
                    "count": 1},
         "as": "p"},
        MOVE_STACK]}],
}]

FORM_SP3 = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [
        {"op": "may", "body": [
            {"op": "move",
             "select": {"zone": "deck", "owner": "you", "from_top": 4},
             "to": "graveyard", "reason": "put"}]},
        {"op": "may", "body": [
            {"op": "choose",
             "select": {"zone": "graveyard", "owner": "you",
                        "filter": {"types": ["creature"], "cost_le": 8,
                                   "evolves_from": "self"},
                        "count": 1},
             "as": "p"},
            MOVE_STACK]}],
}]


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _cand(tid, base):
    c = dict(base)
    c.pop("source", None)
    c.pop("gaps", None)
    return c


def test_targets_still_in_rejects():
    rows = _rows()
    conv_ids = {c["id"] for c in all_cards(CONVERTED)}
    for t in ("dm25rp1-018", "dm25rp2-sp3", "dm25ex1-069"):
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["evolution_base_from_graveyard"]


def test_partial_forms():
    rows = _rows()
    p = rows["dm25rp1-018"]["partial"]
    cand = _cand("dm25rp1-018", {**p, "abilities": FORM_018})
    assert cand["keywords"] == ["g_strike"]
    d = parse_card(cand, TABLES)
    assert len(d.abilities) >= 1
    p = rows["dm25rp2-sp3"]["partial"]
    cand = _cand("dm25rp2-sp3", {**p, "abilities": FORM_SP3})
    assert cand["keywords"] == ["g_strike", "blocker", "double_breaker"]
    d = parse_card(cand, TABLES)
    assert len(d.abilities) >= 1
    p = rows["dm25ex1-069"]["partial"]
    cand = _cand("dm25ex1-069", {**p, "grave_evo": True,
                                 "evolve_zone": "graveyard",
                                 "evolve_from": {"types": ["creature"]}})
    d = parse_card(cand, TABLES)
    assert d.grave_evo is True
    assert d.evolve_from == {"types": ["creature"]}


def test_proto_forms_match():
    assert proto_card("T1021")["abilities"] == FORM_018
    assert proto_card("T1022")["abilities"] == FORM_SP3
    c = proto_card("T1023")
    assert c.get("grave_evo") is True
    assert c.get("evolve_from") == {"types": ["creature"]}
