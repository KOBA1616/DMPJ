"""語彙パイロット第263弾のカード適用テスト（登録形）。

ラウンド298で dragon_mana_buso の6件をすべて新規登録、差し戻しなし。
- 登録6件: dm26ex3-016（相手破壊時 first_time 誘発＋may mekurade look 5）、
  dm26ex3-021（出た時・表向き3枚＋攻撃時 may play_free）、dm26ex3-034
  （出た時・パワー6000破壊＋破壊時・追加ターン if）、dm26ex3-037（呪文・
  4枚までマナ＋龍マナ武装７ play_free distinct_names＋ドラゴン付与）、
  dm26ex3-046（出た時・2枚まで引く＋表向きコスト制限＋シールド S・トリガー）、
  dm26ex3-073（出た時・タップしてマナ＋攻撃時・相手をマナへ）。
- 差し戻しなし。converted 10,081 / rejects 2,256、重複0・漏れ0。
"""
import copy
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card
from dmsim.scenario import build

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"


def _setup(rules, p0, p1=None):
    # tests.conftest の setup と同形。conftest を import すると
    # DMSIM_SKIP_CONVERTED=1 が復活するため、ここで直接 build を呼ぶ。
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": "T001",
                         "seed": 1, "deck_size": 20})

REGISTERED = ("dm26ex3-016", "dm26ex3-021", "dm26ex3-034", "dm26ex3-037",
              "dm26ex3-046", "dm26ex3-073")

DRAGONS = {"cmp": [{"count": {"zone": "mana", "owner": "you",
                              "filter": {"types": ["creature"],
                                         "race_has": "ドラゴン"}}},
                  ">=", 5]}


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


def _triggers(card, event=None):
    return [ab for ab in card.get("abilities") or []
            if ab.get("kind") == "trigger"
            and (event is None or ab["when"].get("event") == event)]


def _drive(e, stop, choose=None, play=None, attack_with=None, attacker=0, limit=800):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "choose_cards" and choose is not None:
            ans = choose(e, d)
            if ans is not None:
                e.answer(ans)
                if stop(e):
                    return
                continue
        if kind == "main" and play is not None:
            ans = play(e, d)
            if ans is not None:
                e.answer(ans)
                if stop(e):
                    return
                continue
        if kind == "attack" and attack_with is not None and e.s.active == attacker:
            hit = next((i for i, k in enumerate(keys)
                        if k.startswith(f"attack:{attack_with}:")), None)
            if hit is not None:
                e.answer([hit])
                if stop(e):
                    return
                continue
        if kind == "block":
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "pay_mana":
            e.answer([0])
        elif kind == "yes_no":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if stop(e):
            return
    raise AssertionError("limit reached")


def _in_zone(e, zone, p, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        assert (card.get("source") or {}).get("official") == cid
        assert "第263弾" in (card.get("source") or {}).get("notes", "")


def test_round298_specific_forms():
    c = _converted("dm26ex3-016")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["keywords"] == ["g_strike", "speed_attacker", "triple_breaker"]
    trig = _triggers(c, "move")
    assert len(trig) == 2
    cip = trig[0]
    assert cip["when"] == {"event": "move", "to": "bz", "subject": "self"}
    assert cip["effect"][0]["op"] == "tap"
    buso = trig[1]
    assert buso.get("first_time") is True
    assert buso["when"]["reason"] == "destroy"
    assert buso["when"]["subject"] == {"owner": "opp",
                                        "filter": {"types": ["creature"]}}
    assert buso["if"] == DRAGONS
    may = buso["effect"][0]
    assert may["op"] == "may" and may["body"][0]["op"] == "mekurade"
    assert may["body"][0]["filter"] == {"race_has": "Jack-Pot"}
    assert may["body"][0]["look"] == 5

    c = _converted("dm26ex3-021")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["keywords"] == ["double_breaker"]
    trig = _triggers(c, "move")
    assert len(trig) == 2
    mach = trig[0]  # マッハファイターの展開形（keyword_patterns.yaml と同形）
    assert mach["effect"][0]["mod"] == {
        "allow": [{"action": "attack_creature", "other": {"tapped": False}}]}
    cip = trig[1]
    assert cip["effect"][0]["select"]["from_top"] == 3
    assert cip["effect"][0]["as"] == "pile"
    assert cip["effect"][1]["to"] == "hand"
    assert cip["effect"][1]["select"]["filter"] == {
        "any_of": [{"types": ["spell"]}, {"race_has": "Jack-Pot"}]}
    assert cip["effect"][2]["to"] == "deck"
    assert cip["effect"][2]["position"] == "bottom"
    assert cip["effect"][2]["order"] == "choose"
    atk = _triggers(c, "attack")[0]
    assert atk["if"] == DRAGONS
    pf = atk["effect"][0]["body"][0]
    assert pf["op"] == "play_free"
    assert pf["select"]["zone"] == "hand"
    assert pf["select"]["filter"] == {
        "any_of": [{"race_has": "Jack-Pot"},
                   {"types": ["spell"], "cost_le": 8}]}

    c = _converted("dm26ex3-034")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["keywords"] == ["speed_attacker", "double_breaker"]
    cip = _triggers(c, "move")[0]
    assert cip["when"] == {"event": "move", "to": "bz", "subject": "self"}
    des = cip["effect"][0]
    assert des["op"] == "destroy"
    assert des["select"]["filter"] == {"types": ["creature"],
                                        "power_ge": 6000, "power_le": 6000}
    buso = _triggers(c, "move")[1]
    assert buso["when"]["reason"] == "destroy"
    assert buso["if"] == {"all": [DRAGONS, {"extra_turn": False}]}
    guard = buso["effect"][0]
    assert guard["op"] == "if"
    assert guard["cond"]["cmp"][0]["count"]["zone"] == ["mana", "graveyard"]
    assert guard["cond"]["cmp"][2] == 5
    mv, xt = guard["then"][0]["body"]
    assert mv["op"] == "move" and mv["select"]["count"] == 5
    assert mv["to"] == "deck" and mv["position"] == "bottom"
    assert mv["order"] == "choose"
    assert xt == {"op": "extra_turn", "player": "you"}

    c = _converted("dm26ex3-037")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["types"] == ["spell"] and c["cost"] == 8
    spell = c["spell"]
    assert spell[0]["select"]["from_top"] == 4
    assert spell[1]["op"] == "mana_put"
    cond = spell[2]
    assert cond["op"] == "if"
    assert cond["cond"]["cmp"][2] == 7
    pf = cond["then"][0]
    assert pf["op"] == "play_free"
    assert pf["select"]["zone"] == ["hand", "mana"]
    assert pf["select"]["count"] == "any"
    assert pf["select"]["distinct_names"] is True
    mod = spell[3]
    assert mod["op"] == "modify"
    assert mod["select"]["filter"] == {"types": ["creature"],
                                        "race_has": "ドラゴン"}
    assert mod["mod"]["grant"] == ["speed_attacker"]
    assert mod["mod"]["allow"] == [{"action": "attack_creature",
                                     "other": {"tapped": False}}]
    assert mod["duration"] == "end_of_turn"

    c = _converted("dm26ex3-046")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["keywords"] == ["double_breaker"]
    cip = _triggers(c, "move")[0]
    rep = cip["effect"][0]
    assert rep["op"] == "repeat" and rep["times"] == 2
    assert rep["body"][0]["body"][0] == {"op": "draw", "count": 1}
    choose = cip["effect"][1]["body"][0]
    assert choose["op"] == "choose" and choose["reveal"] is True
    assert choose["as"] == "shown"
    assert choose["select"]["filter"] == {"race_has": "Jack-Pot"}
    guard = cip["effect"][2]
    assert guard["cond"] == {"exists": {"ref": "shown"}}
    mod = guard["then"][0]
    assert mod["mod"] == {"grant": ["cannot_attack"]}
    assert mod["select"]["filter"]["cost_le"] == {"cost_of": "shown"}
    assert mod["duration"] == "until_next_own_turn_start"
    assert mod["dynamic"] is True
    stat = [ab for ab in c["abilities"] if ab["kind"] == "static"][0]
    assert stat["zone"] == "shield" and stat["affects"] == "self"
    assert stat["mod"] == {"grant": ["s_trigger"]}
    assert stat["if"] == DRAGONS

    c = _converted("dm26ex3-073")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["keywords"] == ["g_strike"]
    cip = _triggers(c, "move")[0]
    assert cip["effect"][0]["select"]["from_top"] == 1
    assert cip["effect"][1]["op"] == "mana_put"
    assert cip["effect"][2]["op"] == "tap"
    guard = cip["effect"][3]
    assert guard["op"] == "if"
    assert guard["cond"]["cmp"][0]["count"]["filter"] == {"race_has": "Jack-Pot"}
    assert guard["cond"]["cmp"][2] == 3
    assert guard["then"][0]["as"] == "t2"
    atk = _triggers(c, "attack")[0]
    assert atk["if"] == DRAGONS
    mv = atk["effect"][0]
    assert mv["op"] == "move" and mv["to"] == "mana" and mv["reason"] == "put"
    assert mv["select"] == {"zone": "bz", "owner": "opp",
                            "filter": {"types": ["creature"]}, "count": 1}


def test_round298_shield_static_grants_s_trigger():
    """dm26ex3-046: マナのドラゴン5体でシールド中の本体に S・トリガーが付く。"""
    rules = load_rules()
    e = _setup(rules, {"shield": ["dm26ex3-046"],
                      "mana": ["dm26ex3-073"] * 5}, {})
    cid = next(c for c in e.zlist("shield", 0)
               if e.s.cards[c].defn == "dm26ex3-046")
    assert "s_trigger" in e.chars(cid)["keywords"]
    e2 = _setup(rules, {"shield": ["dm26ex3-046"],
                       "mana": ["dm26ex3-073"] * 4}, {})
    cid2 = next(c for c in e2.zlist("shield", 0)
                if e2.s.cards[c].defn == "dm26ex3-046")
    assert "s_trigger" not in e2.chars(cid2)["keywords"]


def test_round298_attack_trigger_moves_to_mana():
    """dm26ex3-073: マナのドラゴン5体で攻撃誘発が働き、相手クリーチャーを
    持ち主のマナゾーンに置く。"""
    e = _setup(load_rules(), {"bz": ["dm26ex3-073"],
                             "mana": ["dm26ex3-073"] * 5},
              {"bz": ["T001"]})

    def choose(e, d):
        idx = [i for i, o in enumerate(d["options"])
               if e.s.cards[o["cid"]].defn == "T001"]
        assert idx, "T001 が候補に無い"
        return idx[:1]

    _drive(e, lambda e: _in_zone(e, "mana", 1, "T001"),
           choose=choose, attack_with="dm26ex3-073", attacker=0)
    assert _in_zone(e, "mana", 1, "T001")
