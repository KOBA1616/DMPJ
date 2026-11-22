"""語彙パイロット第350弾の対象カード（実カード parse）。

対象は pure な must_attack_next_turn 3件のうち2件で、
ラウンド385で処理:
- dmrp22-021 ドラヴィ圧鬼の巻（新規登録。登録形は意図した
  形と完全一致）
- dm05-014 ファントム・ベール（stale 掃除: canonical の
  dm18-036 が同機構で登録済みで、aliases に dm05-014 を
  含んでいた。rejects 行は reopen で除去されたのが正）

dm23ex3-tr09 は対象外（バトル代替の機構が無いため
rejects に残る。reopen で外れた行は原文どおり復帰済み）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
_conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import all_cards, find, proto_card  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402

TABLES = load_tables()
ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"

MOD_014 = {"op": "modify",
           "select": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"]}, "count": "all"},
           "mod": {"require": ["attack"]},
           "duration": "until_next_own_turn_start"}
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


def test_targets_registered():
    rows = _rows()
    assert len(rows) == 1986
    conv = all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10326
    assert not (ids & set(rows))          # canonical 重なり0
    # 新規登録（dmrp22-021）
    c = find(CONVERTED, "dmrp22-021")
    assert c is not None and c["abilities"] == FORM_021
    assert not (c.get("source") or {}).get("unsupported")
    parse_card(c, TABLES)
    # stale 掃除（dm05-014）: canonical が同機構で登録済み
    assert "dm05-014" not in rows
    canon = find(CONVERTED, "dm18-036")
    assert canon is not None and canon["spell"] == [MOD_014]
    assert "dm05-014" in (canon.get("source") or {}).get("aliases", [])
    left = {rid for rid, r in rows.items()
            if "must_attack_next_turn" in (r.get("gaps") or [])}
    assert left == {"dm23ex3-tr09"}, left


def test_proto_forms_match():
    assert proto_card("T1054")["spell"] == [MOD_014]
    assert proto_card("T1055")["abilities"] == FORM_021
