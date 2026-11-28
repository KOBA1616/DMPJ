"""語彙パイロット第337弾の対象カード（実カード parse）。

対象は pure な evolution_base_from_graveyard 3件で、
ラウンド372で登録済み:
- dm25rp1-018 至高の邪騎 スベルニル（submit 時に aliases
  [dm25rp1-sec17, promoy24-020] が自動記録されたが
  rejects 行ではない）
- dm25rp2-sp3 魔光神官ルドルフ・アルカディア（aliases 5件、
  同上）
- dm25ex1-069 神滅翔天ポッポ・ジュヴィラ（aliases 3件、
  同上。grave_evo 宣言で登録）

evolution_base_from_graveyard の行は残っていない
（ファミリー解消）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
_conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from tests import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

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


def test_targets_registered():
    rows = _rows()
    assert len(rows) <= 2017  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10297  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dm25rp1-018")
    assert c is not None and c["abilities"] == FORM_018
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == [
        "dm25rp1-sec17", "promoy24-020"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = _conv_cache.find(CONVERTED, "dm25rp2-sp3")
    assert c is not None and c["abilities"] == FORM_SP3
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == [
        "dm22ex2-3a", "dm22ex2-3b", "dm22ex2-s05", "dm24ex2-012",
        "dmart13-004"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = _conv_cache.find(CONVERTED, "dm25ex1-069")
    assert c is not None
    assert c.get("grave_evo") is True
    assert c.get("evolve_zone") == "graveyard"
    assert c.get("evolve_from") == {"types": ["creature"]}
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == [
        "dmex08-120", "dmex16-060", "dmx21-027"]
    d = parse_card(c, TABLES)
    assert d.grave_evo is True
    left = {rid for rid, r in rows.items()
            if "evolution_base_from_graveyard" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


def test_proto_forms_match():
    assert proto_card("T1021")["abilities"] == FORM_018
    assert proto_card("T1022")["abilities"] == FORM_SP3
    c = proto_card("T1023")
    assert c.get("grave_evo") is True
    assert c.get("evolve_from") == {"types": ["creature"]}
