"""語彙パイロット第338弾の対象カード（実カード parse）。

対象は pure な opponent_chooses_deck_position 4件で、
ラウンド373で登録済み:
- dm22rp1-034 氷結呪文「フリズン」（シビルカウントの常在型は
  partial の形のまま。呪文本体は modal の player: opp）
- dm23rp1-035 Uta-Awase選手宣誓のスピーチ（stp_spell は
  partial の形のまま。本体は player: {owner_of: el}）
- dm25rp4-036 ツインヘッドの海幻（超魂Xの常在型は partial の
  形のまま。出た時の誘発を追加）
- dmrp16-s02 頻波羅 ビリヤ棒ド（ムゲンクライムと出た時の
  誘発は partial の形のまま。攻撃時の誘発を追加）

opponent_chooses_deck_position の行は残っていない
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


def test_targets_registered():
    rows = _rows()
    assert len(rows) == 2013
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10301
    assert not (ids & set(rows))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dm22rp1-034")
    assert c is not None and c["spell"] == SPELL_034
    assert c["abilities"] == STATIC_034
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.spell) == 2
    c = _conv_cache.find(CONVERTED, "dm23rp1-035")
    assert c is not None and c["spell"] == SPELL_035
    assert c["stp_spell"] == STP_035
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.spell) == 2 and len(d.stp_spell) == 1
    c = _conv_cache.find(CONVERTED, "dm25rp4-036")
    assert c is not None and c["abilities"] == FORM_036
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
    c = _conv_cache.find(CONVERTED, "dmrp16-s02")
    assert c is not None and c["abilities"] == FORM_S02
    assert c["mugen_climb"] == {"tap": 3, "cost": 3,
                                "civs": ["water"]}
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 2
    left = {rid for rid, r in rows.items()
            if "opponent_chooses_deck_position" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


def test_proto_forms_match():
    assert proto_card("T1024")["spell"] == SPELL_034
    assert proto_card("T1025")["spell"] == SPELL_035
    assert proto_card("T1026")["abilities"] == FORM_036
    assert proto_card("T1027")["abilities"] == FORM_S02
