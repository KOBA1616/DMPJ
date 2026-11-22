"""語彙パイロット第349弾の対象カード（実カード parse）。

対象は pure な summon_lock 4件のうち3件（未登録、rejects 残存）:
- promoy11-083 鬼丸「Ｅｎｄ」
- promoy12-036 激流剣砲 カツ∞キング
- promoy12-085 漢のキズナ カツブードン
（いずれも partial は能力を持たず、全体を組む）

dmx25-s07 は対象外（partial の原文が断片のみで登録の基礎が
ないため rejects に残る）。

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

def _lock5(name_has):
    return [{"kind": "static",
             "affects": {"zone": z, "owner": "you",
                         "filter": {"types": ["exile_creature"],
                                    "name_has": name_has}},
             "mod": {"deny": ["enter_bz"]}}
            for z in ("hand", "graveyard", "mana", "deck", "shield")]


LOCK_ZENITH = {
    "kind": "static",
    "affects": {"zone": "hand", "owner": "any",
                "filter": {"types": ["creature"], "race_has": "ゼニス"}},
    "mod": {"deny": ["summon"]},
}
BATTLE_ZENITH = {
    "kind": "static", "affects": "self",
    "mod": {"battle_power": {"amount": 11000,
                             "opponent_filter": {"race_has": "ゼニス"}}},
}
CIP_036 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "destroy",
                "select": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"],
                                      "keyword": "blocker"},
                           "count": "all"}},
               {"op": "may", "body": [{"op": "draw", "count": 1}]}],
}
LOCK_036 = _lock5("剣砲")
CIP_085 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "may",
                "body": [{"op": "move",
                          "select": {"zone": "bz", "owner": "you",
                                     "filter": {"types": ["creature"]},
                                     "count": 1,
                                     "exclude": [{"ref": "self"}]},
                          "to": "graveyard", "reason": "destroy",
                          "as": "dead"}]},
               {"op": "if",
                "cond": {"cmp": [{"count": {"ref": "dead"}}, ">=", 1]},
                "then": [{"op": "choose",
                          "select": {"zone": "deck", "owner": "you",
                                     "look": True,
                                     "filter": {"types": ["exile_creature"]},
                                     "count": 1},
                          "as": "found"},
                         {"op": "may",
                          "body": [{"op": "move",
                                    "select": {"ref": "found",
                                               "count": "all"},
                                    "to": "hand", "reason": "draw"}]},
                         {"op": "shuffle"}]}],
}
LOCK_085 = _lock5("漢のキズナ カツブードン")

FORM_083 = [LOCK_ZENITH, BATTLE_ZENITH]
FORM_036 = [CIP_036] + LOCK_036
FORM_085 = [CIP_085] + LOCK_085


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
    for t in ("promoy11-083", "promoy12-036", "promoy12-085"):
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["summon_lock"]


def test_partial_forms():
    rows = _rows()
    for tid, form in (("promoy11-083", FORM_083),
                      ("promoy12-036", FORM_036),
                      ("promoy12-085", FORM_085)):
        p = rows[tid]["partial"]
        assert not p.get("abilities")
        d = parse_card(_cand(tid, {**p, "abilities": form}), TABLES)
        assert len(d.abilities) >= 2


def test_proto_forms_match():
    assert proto_card("T1050")["abilities"] == FORM_083
    assert proto_card("T1051")["abilities"] == FORM_036
    assert proto_card("T1052")["abilities"] == FORM_085
