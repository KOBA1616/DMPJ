"""語彙パイロット第267弾のカード適用テスト（登録形）。

ラウンド302で rinne の3件を新規登録、差し戻しなし。
- 登録3件: dm26rp3-s011（天地命動 バラギアラ / 輪廻虹災。ツインパクト。
  CIP マナ全アンタップ／輪廻∞チャージ／呪文面は上5枚から各文明1枚ずつ
  実行、残りを山札の下へ）、dmex08-258（天地命動 バラギアラ / 輪廻暴炎。
  呪文面は1体にスピードアタッカー付与＋合計3000以下を破壊）、
  dmrp08-mh05（天地命動 バラギアラ / 天上天下輪廻独尊。呪文面は自分の
  クリーチャー全員 +8000＋ワールド・ブレイカー／相手全員に
  must_attack_creature）。
- dm26rp3-sec012 は dm26rp3-s011 の同名別印刷として aliases に折り畳まれた。
  dmrp08-mh04 は dmex08-258 の同名別印刷として aliases に折り畳まれた。
- converted 10,097 / rejects 2,239、重複0・漏れ0。
- 付記: 第267弾の schema 再生成で via 列挙への rinne 追加が漏れており、
  submit がスキーマ不一致で失敗したため、data/schema/card.schema.json を
  再生成して補った（差分は via enum への "rinne" 1行のみ）。
"""
import copy
import json
import os
from pathlib import Path

import pytest

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


REGISTERED = ("dm26rp3-s011", "dmex08-258", "dmrp08-mh05")


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


def _face(card):
    return card["faces"][0]


def _spell_face(card):
    return card["faces"][1]


def _drive(e, stop, choose=None, play=None, limit=800):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "choose_evo_source":
            e.answer([0])
            if stop(e):
                return
            continue
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
        if kind == "attack":
            if "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
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


def _count_zone(e, zone, p, defn):
    return sum(1 for c in e.zlist(zone, p)
               if e.s.cards[c].defn == defn)


def _cid(e, zone, p, defn):
    for c in e.zlist(zone, p):
        if e.s.cards[c].defn == defn:
            return c
    raise KeyError(defn)


def _play_key(key, seen, player=0):
    def play(e, d):
        if e.s.active != player:
            return None
        keys = [o["key"] for o in d["options"]]
        if key in keys and not seen.get("opt"):
            seen["opt"] = True
            return [keys.index(key)]
        return None
    return play


def _play(defn, seen, max_n=1, player=0):
    def play(e, d):
        if e.s.active != player:
            return None
        keys = [o["key"] for o in d["options"]]
        if f"play:{defn}" in keys and seen["n"] < max_n:
            seen["n"] += 1
            return [keys.index(f"play:{defn}")]
        return None
    return play


CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self",
                "reason": "summon"},
       "effect": [{"op": "untap",
                   "select": {"zone": "mana", "owner": "you",
                              "count": "all"}}]}

CHARGE = {"kind": "trigger",
          "when": {"event": "cast", "via": "rinne", "subject": "self"},
          "effect": [{"op": "repeat",
                      "times": {"count": {"zone": "bz", "owner": "you",
                                           "filter": {"name_has":
                                                      "天地命動 バラギアラ"}}},
                      "body": [{"op": "move",
                                "select": {"zone": "deck", "owner": "you",
                                           "from_top": 1},
                                "to": "mana", "reason": "put"}]}]}


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        assert (card.get("source") or {}).get("official") == cid
        face = _face(card)
        assert face["name"] == "天地命動 バラギアラ"
        assert face["types"] == ["creature"]
        assert face["civs"] == ["nature"]
        assert face["cost"] == 9 and face["power"] == 17000
        assert face["races"] == ["マスター・ハザード", "グランセクト"]
        assert face["keywords"] == ["triple_breaker"]
        assert face["rinne"] is True
        assert face["abilities"] == [CIP, CHARGE]
        assert card["mana"] == 1
    assert _converted("dm26rp3-s011")["name"] == \
        "天地命動 バラギアラ / 輪廻虹災"
    assert _converted("dmex08-258")["name"] == \
        "天地命動 バラギアラ / 輪廻暴炎"
    assert _converted("dmrp08-mh05")["name"] == \
        "天地命動 バラギアラ / 天上天下輪廻独尊"
    assert (_converted("dm26rp3-s011").get("source") or {}).get("aliases") == \
        ["dm26rp3-sec012"]
    assert (_converted("dmex08-258").get("source") or {}).get("aliases") == \
        ["dmrp08-mh04"]
    assert (_converted("dmrp08-mh05").get("source") or {}).get("aliases") is None


def test_round302_spell_faces():
    sp = _spell_face(_converted("dm26rp3-s011"))
    assert sp["name"] == "輪廻虹災"
    assert sp["types"] == ["spell"]
    assert sp["civs"] == ["light", "water", "darkness", "fire", "nature"]
    assert sp["cost"] == 10
    ops = sp["spell"]
    assert ops[0] == {"op": "choose",
                      "select": {"zone": "deck", "owner": "you",
                                 "from_top": 5, "look": True, "count": "all"},
                      "reveal": True, "as": "pile"}
    assert [o["op"] for o in ops[1:6]] == ["if"] * 5
    assert [o["cond"]["exists"]["filter"]["civs"] for o in ops[1:6]] == [
        ["light"], ["water"], ["darkness"], ["fire"], ["nature"]]
    for o in ops[1:6]:
        assert o["then"][0]["op"] == "may"
        pf = o["then"][0]["body"][0]
        assert pf["op"] == "play_free" and pf["select"]["count"] == 1
        assert pf["select"]["filter"]["cost_le"] == 9
    assert ops[6] == {"op": "move",
                      "select": {"ref": "pile", "zone": "deck",
                                 "count": "all"},
                      "to": "deck", "reason": "put", "position": "bottom",
                      "order": "choose"}

    sp = _spell_face(_converted("dmex08-258"))
    assert sp["name"] == "輪廻暴炎"
    assert sp["types"] == ["spell"] and sp["civs"] == ["fire"]
    assert sp["cost"] == 3
    assert sp["spell"] == [
        {"op": "modify",
         "select": {"zone": "bz", "owner": "you",
                    "filter": {"types": ["creature"]}, "count": 1},
         "mod": {"grant": ["speed_attacker"]},
         "duration": "end_of_turn"},
        {"op": "destroy",
         "select": {"zone": "bz", "owner": "opp",
                    "filter": {"types": ["creature"]},
                    "total_power_le": 3000}}]

    sp = _spell_face(_converted("dmrp08-mh05"))
    assert sp["name"] == "天上天下輪廻独尊"
    assert sp["types"] == ["spell"] and sp["civs"] == ["nature"]
    assert sp["cost"] == 8
    assert sp["spell"] == [
        {"op": "modify",
         "select": {"zone": "bz", "owner": "you",
                    "filter": {"types": ["creature"]}, "count": "all"},
         "mod": {"power": 8000, "grant": ["world_breaker"]},
         "duration": "end_of_turn", "dynamic": True},
        {"op": "modify",
         "select": {"zone": "bz", "owner": "opp",
                    "filter": {"types": ["creature"]}, "count": "all"},
         "mod": {"must_attack_creature": True},
         "duration": "until_next_own_turn_start", "dynamic": True}]


def test_sec012_and_mh04_alias_level_stale():
    """sec012 / mh04 は aliases に折り畳まれたため、rejects には存在しない。"""
    assert "dm26rp3-sec012" in (
        _converted("dm26rp3-s011").get("source") or {}).get("aliases", [])
    assert "dmrp08-mh04" in (
        _converted("dmex08-258").get("source") or {}).get("aliases", [])
    with pytest.raises(KeyError):
        _reject("dm26rp3-sec012")
    with pytest.raises(KeyError):
        _reject("dmrp08-mh04")


def test_s011_cip_untaps_mana():
    """dm26rp3-s011: 召喚によって出た時、マナをすべてアンタップする。"""
    e = _setup(load_rules(),
               {"hand": ["dm26rp3-s011"], "mana": ["T001"] * 9}, {})
    seen = {}
    _drive(e, lambda e: _in_zone(e, "bz", 0, "dm26rp3-s011")
           and not any(e.s.cards[c].tapped for c in e.zlist("mana", 0)),
           play=_play_key("play:dm26rp3-s011:0", seen))
    assert seen["opt"]


def test_258_rinne_cast_destroys_and_charges():
    """dmex08-258: 輪廻∞で唱える。相手の T001（2000）を破壊し、
    バラギアラは場に残り、1枚チャージされる。"""
    e = _setup(load_rules(),
               {"bz": ["dmex08-258"], "mana": ["T005"] * 3},
               {"bz": ["T001"]})
    seen = {}

    def choose(e, d):
        for i, o in enumerate(d["options"]):
            if e.s.cards[o["cid"]].defn == "T001":
                return [i]
        return [0]

    _drive(e, lambda e: _count_zone(e, "graveyard", 1, "T001") == 1
           and len(e.zlist("mana", 0)) == 4,
           choose=choose, play=_play_key("play:dmex08-258:1:rinne", seen))
    assert seen["opt"]
    assert _in_zone(e, "bz", 0, "dmex08-258")
    assert "dmex08-258" not in [e.s.cards[c].defn
                                for c in e.zlist("graveyard", 0)]
    tapped = [c for c in e.zlist("mana", 0) if e.s.cards[c].tapped]
    assert len(tapped) == 3  # 払った3枚だけタップ。チャージ分はアンタップ


def test_mh05_rinne_cast_buffs():
    """dmrp08-mh05: 輪廻∞で唱える。自分の T001 が +8000 され、
    ワールド・ブレイカーを得て、1枚チャージされる。"""
    e = _setup(load_rules(),
               {"bz": ["dmrp08-mh05", "T001"], "mana": ["T001"] * 8}, {})
    seen = {}

    def stop(e):
        if not _in_zone(e, "bz", 0, "T001"):
            return False
        t001 = _cid(e, "bz", 0, "T001")
        return e.chars(t001)["power"] == 10000 \
            and "world_breaker" in e.chars(t001)["keywords"] \
            and len(e.zlist("mana", 0)) == 9

    _drive(e, stop, play=_play_key("play:dmrp08-mh05:1:rinne", seen))
    assert seen["opt"]
    assert _in_zone(e, "bz", 0, "dmrp08-mh05")
