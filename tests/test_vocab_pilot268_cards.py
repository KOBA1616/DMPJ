"""語彙パイロット第268弾のカード適用テスト（登録形）。

ラウンド303で dogiragon_gacha の4件を新規登録、差し戻しなし。
- 登録4件: dmd34-001（宿命のドギラゴン銀刃。革命チェンジ：火/自然ドラゴン／
  W・ブレイカー／CIP ガチャ3度）、dmd34-003（超DX ブリキンジェット。
  スピードアタッカー／CIP ガチャ1度）、dmd34-004（ドギラゴン・チャンス。
  S・トリガー呪文／ガチャ2度）、dmd34-008（運命の新星 クシカーツ。
  CIP ガチャ1度）。
- タップイン（マナゾーンに置く時タップして置く）は多色カードの一般則
  （core.py: 多色カードはマナにタップして置かれる）で処理されるため
  面項目なし。dmd34-001 / dmd34-008 は火/自然の多色。
- converted 10,101 / rejects 2,235、重複0・漏れ0。dogiragon_gacha
  ギャップは残り0件でファミリー解消。
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


REGISTERED = ("dmd34-001", "dmd34-003", "dmd34-004", "dmd34-008")


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


def _drive(e, stop, choose=None, play=None, limit=800):
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


def _in_bz(e, p, defn):
    return any(e.s.cards[c].defn == defn and e.s.cards[c].controller == p
               for c in e.zlist("bz", p))


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


def _pick_t001(e, d):
    """choose_cards で T001 が候補にあれば1枚選ぶ（ガチャの各効果の選択先を固定する）。"""
    idx = [i for i, o in enumerate(d["options"])
           if e.s.cards[o["cid"]].defn == "T001"]
    return idx[:1] if idx else None


def _gacha_done(n):
    """ガチャが n 回ぶん解決し終えたら止める（タスクが消え、公開記録が n 件）。"""
    def stop(e):
        recs = [r for r in e.s.pub if r["kind"] == "gacha"]
        return (len(recs) == n
                and not any(t.get("t") == "gacha" for t in e.s.tasks))
    return stop


DECLARE_001 = {"kind": "declare",
               "zone": "hand",
               "when": {"event": "attack",
                        "subject": {"owner": "you",
                                    "filter": {"civs": ["fire", "nature"],
                                               "race_has": "ドラゴン"}}},
               "effect": [{"op": "swap",
                           "out": {"ref": "event.subject"},
                           "in": {"ref": "self"}}]}


def _cip(times):
    return {"kind": "trigger",
            "when": {"event": "move", "to": "bz", "subject": "self"},
            "effect": [{"op": "gacha", "kind": "dogiragon",
                        "times": times}]}


def test_registered_forms():
    c = _converted("dmd34-001")
    parse_card(copy.deepcopy(c), TABLES)
    assert (c.get("source") or {}).get("official") == "dmd34-001"
    assert c["name"] == "宿命のドギラゴン銀刃"
    assert c["types"] == ["creature"]
    assert c["civs"] == ["fire", "nature"]
    assert c["cost"] == 7 and c["power"] == 9000
    assert c["races"] == ["メガ・コマンド・ドラゴン", "革命軍", "ハムカツ団"]
    assert c["mana"] == 1
    assert c["keywords"] == ["double_breaker"]
    assert c["abilities"] == [DECLARE_001, _cip(3)]

    c = _converted("dmd34-003")
    parse_card(copy.deepcopy(c), TABLES)
    assert (c.get("source") or {}).get("official") == "dmd34-003"
    assert c["name"] == "超DX ブリキンジェット"
    assert c["types"] == ["creature"]
    assert c["civs"] == ["fire"]
    assert c["cost"] == 5 and c["power"] == 5000
    assert c["races"] == ["メガ・ドラゴン", "革命軍", "ハムカツ団"]
    assert c["mana"] == 1
    assert c["keywords"] == ["speed_attacker"]
    assert c["abilities"] == [_cip(1)]

    c = _converted("dmd34-004")
    parse_card(copy.deepcopy(c), TABLES)
    assert (c.get("source") or {}).get("official") == "dmd34-004"
    assert c["name"] == "ドギラゴン・チャンス"
    assert c["types"] == ["spell"]
    assert c["civs"] == ["fire"]
    assert c["cost"] == 3
    assert c["mana"] == 1
    assert c["keywords"] == ["s_trigger"]
    assert c["spell"] == [{"op": "gacha", "kind": "dogiragon", "times": 2}]

    c = _converted("dmd34-008")
    parse_card(copy.deepcopy(c), TABLES)
    assert (c.get("source") or {}).get("official") == "dmd34-008"
    assert c["name"] == "運命の新星 クシカーツ"
    assert c["types"] == ["creature"]
    assert c["civs"] == ["fire", "nature"]
    assert c["cost"] == 3 and c["power"] == 4000
    assert c["races"] == ["メガ・ドラゴン", "革命軍", "ハムカツ団"]
    assert c["mana"] == 1
    assert c.get("keywords") is None
    assert c["abilities"] == [_cip(1)]

    for cid in REGISTERED:
        assert (_converted(cid).get("source") or {}).get("aliases") is None


def test_round303_no_rejects_left():
    """4件とも rejects から消え、dogiragon_gacha ギャップは残っていない。"""
    for cid in REGISTERED:
        with pytest.raises(KeyError):
            _reject(cid)
    for line in open(REJECTS, encoding="utf-8"):
        r = json.loads(line)
        assert "dogiragon_gacha" not in r.get("gaps", [])


def test_001_cip_gacha_times_three():
    """dmd34-001: 手札から出すと CIP でガチャが3度回る（公開記録3件）。"""
    e = _setup(load_rules(),
               {"hand": ["dmd34-001"], "bz": ["T001"],
                "mana": ["T005"] * 4 + ["T001"] * 3},
               {"bz": ["T001"]})
    seen = {}
    _drive(e, _gacha_done(3), choose=_pick_t001,
           play=_play_key("play:dmd34-001", seen))
    assert seen["opt"]
    assert _in_bz(e, 0, "dmd34-001")
    recs = [r for r in e.s.pub if r["kind"] == "gacha"]
    assert len(recs) == 3
    assert all(1 <= r["result"] <= 6 for r in recs)


def test_003_cip_gacha_times_one():
    """dmd34-003: 手札から出すと CIP でガチャが1度回る。"""
    e = _setup(load_rules(),
               {"hand": ["dmd34-003"], "bz": ["T001"],
                "mana": ["T005"] * 5},
               {"bz": ["T001"]})
    seen = {}
    _drive(e, _gacha_done(1), choose=_pick_t001,
           play=_play_key("play:dmd34-003", seen))
    assert seen["opt"]
    assert _in_bz(e, 0, "dmd34-003")
    recs = [r for r in e.s.pub if r["kind"] == "gacha"]
    assert len(recs) == 1


def test_004_spell_gacha_times_two():
    """dmd34-004: 唱えるとガチャが2度回り、呪文は墓地へ行く。"""
    e = _setup(load_rules(),
               {"hand": ["dmd34-004"], "bz": ["T001"],
                "mana": ["T005"] * 3},
               {"bz": ["T001"]})
    seen = {}
    _drive(e, _gacha_done(2), choose=_pick_t001,
           play=_play_key("play:dmd34-004", seen))
    assert seen["opt"]
    assert _in_zone(e, "graveyard", 0, "dmd34-004")
    recs = [r for r in e.s.pub if r["kind"] == "gacha"]
    assert len(recs) == 2


def test_008_cip_gacha_times_one():
    """dmd34-008: 手札から出すと CIP でガチャが1度回る。"""
    e = _setup(load_rules(),
               {"hand": ["dmd34-008"], "bz": ["T001"],
                "mana": ["T005"] * 2 + ["T001"]},
               {"bz": ["T001"]})
    seen = {}
    _drive(e, _gacha_done(1), choose=_pick_t001,
           play=_play_key("play:dmd34-008", seen))
    assert seen["opt"]
    assert _in_bz(e, 0, "dmd34-008")
    recs = [r for r in e.s.pub if r["kind"] == "gacha"]
    assert len(recs) == 1


def test_001_revolution_change_swaps():
    """dmd34-001: 火/自然ドラゴン（dmd34-008）の攻撃時に宣言すると、
    攻撃クリーチャーと手札の dmd34-001 が入れ替わる。"""
    e = _setup(load_rules(),
               {"bz": ["dmd34-008"], "hand": ["dmd34-001"]},
               {"bz": ["T001"]})
    seen_keys = []
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "declare_attack":
            seen_keys.append(list(keys))
            hit = next((i for i, k in enumerate(keys)
                        if k.startswith("declare:dmd34-001")), None)
            e.answer([hit] if hit is not None else [])
        elif d["kind"] == "attack":
            atk = next((i for i, k in enumerate(keys)
                        if k.startswith("attack:dmd34-008")), None)
            if atk is not None and e.s.active == 0:
                e.answer([atk])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif d["kind"] == "block":
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if _in_bz(e, 0, "dmd34-001") and _in_zone(e, "hand", 0, "dmd34-008"):
            break
    else:
        raise AssertionError("limit reached")
    assert _in_bz(e, 0, "dmd34-001")
    assert _in_zone(e, "hand", 0, "dmd34-008")
    assert any(k.startswith("declare:dmd34-001")
               for ks in seen_keys for k in ks)
