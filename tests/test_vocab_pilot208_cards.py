"""語彙パイロット第208弾のカード適用テスト（変換形ビルド）。

ラウンド244: j_crime 単独8件を全件新規登録する。JクライムN は攻撃
誘発から op swap（out_to: graveyard）で入れ替えるイディオム（第208弾）。

- dm26rp3-037 の墓地回収は「ジョーカーズ・カード」（種族のみで選ぶ）
- dm26rp3-s004 / sec005 の「そうしたら」は may の move を as で束ね、
  exists で分岐する
"""
import copy
import json
from pathlib import Path

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"


def _reject(cid):
    for line in open(REJECTS, encoding="utf-8"):
        r = json.loads(line)
        if r["id"] == cid:
            return r
    raise KeyError(cid)


def _base(cid, note):
    r = _reject(cid)
    card = copy.deepcopy(r["partial"])
    card["text"] = r["text"]
    src = card.setdefault("source", {})
    src.pop("unsupported", None)
    src["notes"] = note
    card.setdefault("abilities", [])
    card.setdefault("keywords", [])
    return card


def _jc(n):
    return {"kind": "trigger",
            "when": {"event": "attack", "subject": "self"},
            "effect": [{"op": "may", "body": [
                {"op": "swap", "out": {"ref": "self"},
                 "in": {"zone": "graveyard", "owner": "you",
                        "filter": {"types": ["creature"],
                                   "races": ["ジョーカーズ"],
                                   "cost_le": n},
                        "count": 1},
                 "out_to": "graveyard"}]}]}


def _cip(effect):
    return {"kind": "trigger",
            "when": {"event": "move", "to": "bz", "subject": "self"},
            "effect": effect}


def _destroy1():
    return {"op": "move",
            "select": {"zone": "bz", "owner": "opp",
                       "filter": {"types": ["creature"]}, "count": 1},
            "to": "graveyard", "reason": "destroy"}


def build():
    """登録8件を組み立てる。"""
    cards = []
    note = "再変換ラウンド244。第208弾 j_crime の再変換。入れ替えは op swap で表す。"

    c = _base("dm26rp3-016", note)
    c["keywords"] = ["g_strike", "double_breaker"]
    c["abilities"] = [_cip([_destroy1()]), _jc(8)]
    cards.append(c)

    c = _base("dm26rp3-037", note)
    c["abilities"] = [
        _cip([{"op": "may", "body": [
                  {"op": "move",
                   "select": {"zone": "deck", "owner": "you", "from_top": 4,
                              "count": "all"},
                   "to": "graveyard", "reason": "put"}]},
              {"op": "may", "body": [
                  {"op": "move",
                   "select": {"zone": "graveyard", "owner": "you",
                              "filter": {"races": ["ジョーカーズ"]},
                              "count": 1},
                   "to": "hand", "reason": "return"}]}]),
        _jc(6)]
    cards.append(c)

    c = _base("dm26rp3-062", note)
    c["abilities"] = [
        _cip([{"op": "move",
               "select": {"zone": "bz", "owner": "opp",
                          "filter": {"types": ["creature"]}, "count": 1},
               "to": "deck", "position": "bottom", "reason": "return"}]),
        _jc(4)]
    cards.append(c)

    c = _base("dm26rp3-064", note)
    c["abilities"] = [
        _jc(6),
        {"kind": "trigger",
         "when": {"event": "move", "from": "bz", "subject": "self"},
         "effect": [{"op": "modify",
                     "select": {"zone": "bz", "owner": "opp",
                                "filter": {"types": ["creature"]}, "count": 1},
                     "mod": {"power": -4000}, "duration": "end_of_turn"}]}]
    cards.append(c)

    c = _base("dm26rp3-065", note)
    c["abilities"] = list(c["abilities"]) + [_jc(4)]
    cards.append(c)

    for cid in ("dm26rp3-s004", "dm26rp3-sec005"):
        c = _base(cid, note)
        c["abilities"] = [
            _cip([{"op": "discard",
                   "select": {"zone": "hand", "owner": "opp", "count": 1}},
                  {"op": "may", "body": [
                      {"op": "move",
                       "select": {"zone": "hand", "owner": "you", "count": 1},
                       "to": "graveyard", "reason": "discard", "as": "d"}]},
                  {"op": "if", "cond": {"exists": {"ref": "d"}},
                   "then": [{"op": "modify",
                             "select": {"zone": "bz", "owner": "opp",
                                        "filter": {"types": ["creature"]},
                                        "count": 1},
                             "mod": {"power": -4000},
                             "duration": "end_of_turn"}]}]),
            _jc(8)]
        cards.append(c)

    c = _base("dm26rp3-sec023", note)
    c["abilities"] = list(c["abilities"]) + [_jc(4)]
    cards.append(c)

    return {"cards": cards}


def test_build_forms_parse():
    built = build()
    assert len(built["cards"]) == 8
    for card in built["cards"]:
        parse_card(copy.deepcopy(card), TABLES)


def test_jcrime_forms_present():
    for card in build()["cards"]:
        flat = json.dumps(card["abilities"], ensure_ascii=False)
        assert '"swap"' in flat, card["id"]
