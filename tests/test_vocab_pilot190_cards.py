"""語彙パイロット第190弾のカード適用テスト（登録形）。

ラウンド226で ex_life 単独9件のうち7件を登録、2件を差し戻し。
- 登録7件: converted.yaml から読み、EXTRA の節が abilities に含まれることを確認。
- dmex18-014: 攻撃終了時の支払い付き実行の語彙が無いため差し戻し
  （新ギャップ paid_play_from_hand_graveyard）。第1節の文明数コスト軽減は
  partial に残した。
- dmsd19-001: プレイヤー選択の語彙が無いため差し戻し
  （新ギャップ choose_player_effect）。CIP のマナアンタップは partial に残した。
"""
import copy
import json
from pathlib import Path

from dmsim.cards import cardstore

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

RET = {"op": "may", "body": [
    {"op": "move",
     "select": {"zone": ["mana", "graveyard"], "owner": "you",
                "count": 1, "up_to": True},
     "to": "hand", "reason": "return"}]}
DISCARD = {"op": "move",
           "select": {"zone": "hand", "owner": "opp", "count": 1,
                      "chooser": "opp"},
           "to": "graveyard", "reason": "discard"}
DESTROY_OPP = {"op": "destroy",
               "select": {"zone": "bz", "owner": "opp",
                          "filter": {"types": ["creature"]},
                          "count": 1, "up_to": True}}
DRAW_AND_CAST = [
    {"op": "may", "body": [{"op": "draw", "count": 1}]},
    {"op": "may", "body": [
        {"op": "play_free",
         "select": {"zone": "hand", "owner": "you",
                    "filter": {"types": ["spell"], "cost_le": 9},
                    "count": 1, "up_to": True}}]},
]

EXTRA = {
    "dm26ex1-n014": [
        {"kind": "trigger", "when": {"event": "tap", "subject": "self"},
         "effect": [RET, DISCARD]},
        {"kind": "trigger",
         "when": {"event": "move", "from": "shield",
                  "subject": {"exlife_of": "self"}},
         "effect": [RET, DISCARD]},
    ],
    "dmex19-021": [
        {"kind": "static", "affects": "self",
         "mod": {"power": {"amount": 1000,
                           "count": {"zone": "shield", "owner": "you"}}}},
        {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
         "effect": [{"op": "move",
                     "select": {"zone": "bz", "owner": "opp",
                                "filter": {"types": ["creature"]},
                                "count": 1, "up_to": True},
                     "to": "deck", "reason": "put", "position": "bottom"}]},
        {"kind": "trigger", "when": {"event": "attack", "subject": "self"},
         "effect": [{"op": "may", "body": [
             {"op": "reveal_until", "filter": {}, "count": 2, "as": "seen"},
             {"op": "choose", "select": {"ref": "seen", "count": 1},
              "as": "toshield"},
             {"op": "move", "select": {"ref": "toshield"},
              "to": "shield", "reason": "put"},
             {"op": "move",
              "select": {"ref": "seen", "exclude": {"ref": "toshield"}},
              "to": "hand", "reason": "put"}]}]},
    ],
    "dmex19-m13": [
        {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
         "effect": [{"op": "modify",
                     "select": {"zone": "bz", "owner": "opp",
                                "filter": {"types": ["creature"]}},
                     "mod": {"ignore": ["all"]},
                     "duration": "until_next_own_turn_start",
                     "dynamic": True}]},
        {"kind": "trigger",
         "when": {"event": "summon",
                  "subject": {"owner": "opp", "filter": {"cost_le": 9}}},
         "if": {"is_turn": "opp"}, "effect": DRAW_AND_CAST},
        {"kind": "trigger",
         "when": {"event": "cast",
                  "subject": {"owner": "opp", "filter": {"cost_le": 9}}},
         "if": {"is_turn": "opp"}, "effect": DRAW_AND_CAST},
    ],
    "dmsd18-001": [
        {"kind": "static", "affects": "self",
         "mod": {"deny": [{"action": "be_chosen",
                            "other": {"types": ["spell"],
                                     "multicolor": False}}]}},
        {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
         "effect": [DESTROY_OPP]},
        {"kind": "trigger",
         "when": {"event": "move", "from": "shield",
                  "subject": {"exlife_of": "self"}},
         "effect": [DESTROY_OPP]},
    ],
    "dmsd18-002": [
        {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
         "effect": [{"op": "play_free",
                     "select": {"zone": "graveyard", "owner": "you",
                                "filter": {"types": ["creature"],
                                           "cost_le": 4},
                                "count": 1, "up_to": True}}]},
    ],
    "dmsd19-003": [
        {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
         "effect": [{"op": "may", "body": [
             {"op": "play_free",
              "select": {"zone": "hand", "owner": "you",
                         "filter": {"cost_le": 4},
                         "count": 1, "up_to": True}}]}]},
    ],
    "dmsd19-009": [
        {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
         "effect": [{"op": "may", "body": [
             {"op": "play_free",
              "select": {"zone": "mana", "owner": "you",
                         "filter": {"race_has": "ディスタス"},
                         "count": 1, "up_to": True}}]}]},
    ],
}


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject(cid):
    for line in open(REJECTS, encoding="utf-8"):
        r = json.loads(line)
        if r["id"] == cid:
            return r
    raise KeyError(cid)


def test_ex_life_cards_parse():
    for cid, extra in EXTRA.items():
        card = _converted(cid)
        for e in extra:
            assert e in (card.get("abilities") or []), f"{cid}: 節が無い: {e}"
        parse_card(copy.deepcopy(card), TABLES)


def test_ex_life_bounces_keep_solved_clauses():
    """差し戻し2件: 新ギャップで rejects に戻り、解けた節が partial に残る。"""
    r = _reject("dmex18-014")
    assert r["gaps"] == ["paid_play_from_hand_graveyard"]
    assert r["partial"].get("abilities"), "dmex18-014: 文明数コスト軽減が残っていない"
    # dmsd19-001 は choose_player_effect で差し戻した後、ラウンド228（第192弾）で登録済み。
    # 解けていた CIP アンタップの節は登録後のカードに残っている
    assert _converted("dmsd19-001")["id"] == "dmsd19-001"
    assert _converted("dmsd19-001").get("abilities"), "dmsd19-001: CIP アンタップが残っていない"


def test_cost_per_civ_parses():
    """dmex18-014 第1節: 文明1つにつきコスト-1 は既存語彙で書ける。
    （第2節の支払い付き実行が無いためラウンドでは差し戻し。
    差し戻し後の partial には第1節がそのまま残っている）"""
    card = copy.deepcopy(_reject("dmex18-014")["partial"])
    assert {"kind": "static",
            "affects": {"zone": "hand", "owner": "you"},
            "mod": {"cost": {"amount": -1,
                             "count": {"civ_count": {"ref": "self"}}}}} \
        in (card.get("abilities") or [])
    parse_card(card, TABLES)
