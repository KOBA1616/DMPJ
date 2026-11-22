"""語彙パイロット第350弾の対象カード（実カード parse）。

対象は pure な must_attack_next_turn 3件のうち2件（未登録、
rejects 残存）:
- dm05-014 ファントム・ベール（呪文）
- dmrp22-021 ドラヴィ圧鬼の巻（タマシード。partial の
  シンカパワー誘発はそのまま使う）

dm23ex3-tr09 は対象外（バトル代替の機構が無く全体を
組めないため rejects に残る）。

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

MOD_014 = {"op": "modify",
           "select": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"]}, "count": "all"},
           "mod": {"require": ["attack"]},
           "duration": "until_next_opp_turn_end"}
CIP_021 = {"kind": "trigger",
           "when": {"event": "move", "to": "bz", "subject": "self"},
           "effect": [{"op": "modify",
                       "select": {"zone": "bz", "owner": "opp",
                                  "filter": {"types": ["creature"]},
                                  "count": "all"},
                       "mod": {"require": ["attack"]},
                       "duration": "until_next_own_turn_start"}]}
SHINKA_021 = {"kind": "trigger",
              "when": {"event": "evolve_base", "subject": "self"},
              "effect": [{"op": "modify",
                          "select": {"ref": "event.top"},
                          "mod": {"gain": [{"kind": "trigger",
                                            "first_time": True,
                                            "when": {"event": "battle_win",
                                                     "subject": "self"},
                                            "effect": [{"op": "untap",
                                                        "select": {"ref": "self",
                                                                   "count": 1}}]}]},
                          "duration": "until_next_own_turn_start"}]}

FORM_021 = [CIP_021, SHINKA_021]


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
    for t in ("dm05-014", "dmrp22-021"):
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["must_attack_next_turn"]


def test_partial_forms():
    rows = _rows()
    # 呪文（dm05-014）: partial に spell は無く、組んだ形で parse
    p = rows["dm05-014"]["partial"]
    d = parse_card(_cand("dm05-014", {**p, "spell": [MOD_014]}), TABLES)
    assert len(d.spell) == 1
    # タマシード（dmrp22-021）: partial の誘発＋CIP で parse
    p = rows["dmrp22-021"]["partial"]
    assert p["abilities"] == [SHINKA_021]
    d = parse_card(_cand("dmrp22-021", {**p, "abilities": FORM_021}), TABLES)
    assert len(d.abilities) >= 2


def test_proto_forms_match():
    assert proto_card("T1054")["spell"] == [MOD_014]
    assert proto_card("T1055")["abilities"] == FORM_021
