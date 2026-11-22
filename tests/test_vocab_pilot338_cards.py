"""語彙パイロット第338弾の対象カード（実カード parse）。

対象は pure な opponent_chooses_deck_position 4件（未登録、
rejects 残存）:
- dm22rp1-034 氷結呪文「フリズン」（partial はシビルカウントの
  常在型を持ち、呪文本体だけが欠けていた）
- dm23rp1-035 Uta-Awase選手宣誓のスピーチ（partial は本体の
  choose と stp_spell を持ち、modal だけが欠けていた）
- dm25rp4-036 ツインヘッドの海幻（partial は超魂Xの常在型を
  持ち、出た時の誘発だけが欠けていた）
- dmrp16-s02 頻波羅 ビリヤ棒ド（partial はムゲンクライムと
  出た時の誘発を持ち、攻撃時の誘発だけが欠けていた）

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


def _modal_deck(var, player):
    return {"op": "modal", "player": player, "modes": [
        [{"op": "move", "select": {"ref": var, "count": "all"},
          "to": "deck", "reason": "put", "position": "top"}],
        [{"op": "move", "select": {"ref": var, "count": "all"},
          "to": "deck", "reason": "put", "position": "bottom"}]]}


SPELL_034 = [
    {"op": "choose",
     "select": {"zone": "bz", "owner": "opp",
                "filter": {"types": ["creature", "tamaseed"]},
                "count": 1},
     "as": "target"},
    _modal_deck("target", "opp"),
]
STATIC_034 = [{
    "kind": "static", "zone": "shield", "affects": "self",
    "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                              "filter": {"civs": ["water"],
                                         "types": ["creature",
                                                   "tamaseed"]}}},
                    ">=", 2]},
    "mod": {"allow": ["s_trigger"]},
}]

SPELL_035 = [
    {"op": "choose",
     "select": {"zone": "bz", "owner": "any", "count": 1},
     "as": "el"},
    _modal_deck("el", {"owner_of": "el"}),
]
STP_035 = [{
    "op": "modify",
    "select": {"zone": "bz", "owner": "opp",
               "filter": {"types": ["creature"]}, "count": 2},
    "mod": {"deny": ["attack_player", "attack_creature", "block"]},
    "duration": "until_next_own_turn_start",
}]

FORM_036 = [
    {"kind": "static", "choukon": True, "affects": "self",
     "mod": {"grant": ["powered_breaker"]}},
    {"kind": "static", "choukon": True, "affects": "self",
     "mod": {"power": 3000}},
    {"kind": "trigger",
     "when": {"event": "move", "to": "bz", "subject": "self"},
     "effect": [
         {"op": "choose",
          "select": {"zone": "bz", "owner": "opp", "count": 1},
          "as": "el"},
         _modal_deck("el", "opp"),
         {"op": "may", "body": [
             {"op": "choose",
              "select": {"zone": "bz", "owner": "you",
                         "filter": {"types": ["creature"],
                                    "any_of": [{"neo": True},
                                               {"evolution": True}]},
                         "count": 1},
              "as": "host"},
             {"op": "put_under",
              "select": {"ref": "self", "count": "all"},
              "onto": {"ref": "host"}}]}]},
]

FORM_S02 = [
    {"kind": "trigger",
     "when": {"event": "move", "to": "bz", "subject": "self"},
     "effect": [{"op": "repeat", "times": 2,
                 "body": [{"op": "may",
                           "body": [{"op": "draw", "count": 1}]}]}]},
    {"kind": "trigger",
     "when": {"event": "attack", "subject": "self"},
     "effect": [{"op": "repeat", "times": 2, "body": [
         {"op": "move",
          "select": {"zone": "hand", "owner": "you", "count": 1,
                     "up_to": True},
          "to": "graveyard", "reason": "discard", "as": "d"},
         {"op": "if", "cond": {"exists": {"ref": "d"}}, "then": [
             {"op": "choose",
              "select": {"zone": "bz", "owner": "opp",
                         "filter": {"types": ["creature"]},
                         "count": 1},
              "as": "el"},
             _modal_deck("el", "opp")]}]}]},
]


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
    for t in ("dm22rp1-034", "dm23rp1-035", "dm25rp4-036",
              "dmrp16-s02"):
        assert t in rows and t not in conv_ids
        assert rows[t].get("gaps") == ["opponent_chooses_deck_position"]


def test_partial_forms():
    rows = _rows()
    p = rows["dm22rp1-034"]["partial"]
    assert p["abilities"] == STATIC_034
    cand = _cand("dm22rp1-034", {**p, "spell": SPELL_034})
    d = parse_card(cand, TABLES)
    assert len(d.spell) == 2
    p = rows["dm23rp1-035"]["partial"]
    assert p["spell"] == SPELL_035[:1]          # choose は既存
    assert p["stp_spell"] == STP_035
    cand = _cand("dm23rp1-035", {**p, "spell": SPELL_035})
    d = parse_card(cand, TABLES)
    assert len(d.spell) == 2 and len(d.stp_spell) == 1
    p = rows["dm25rp4-036"]["partial"]
    assert p["abilities"] == FORM_036[:2]       # 超魂Xは既存
    cand = _cand("dm25rp4-036", {**p, "abilities": FORM_036})
    d = parse_card(cand, TABLES)
    assert len(d.abilities) >= 3
    p = rows["dmrp16-s02"]["partial"]
    assert p["abilities"] == FORM_S02[:1]       # 出た時は既存
    cand = _cand("dmrp16-s02", {**p, "abilities": FORM_S02})
    d = parse_card(cand, TABLES)
    assert len(d.abilities) >= 2


def test_proto_forms_match():
    assert proto_card("T1024")["spell"] == SPELL_034
    assert proto_card("T1025")["spell"] == SPELL_035
    assert proto_card("T1026")["abilities"] == FORM_036
    assert proto_card("T1027")["abilities"] == FORM_S02
