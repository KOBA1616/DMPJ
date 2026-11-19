"""語彙パイロット第270弾のカード適用テスト（登録形）。

ラウンド305で ability_copy の1件を新規登録、差し戻しなし。
- 新規1件: dm26sd1-a005（魔誕の斬将オルゲイト。trigger イベント＋
  use_triggered_ability で相手ターンの相手 CIP をコピー）。
- dm26sd1-n001 は reopen で外れた alias 側の残行: dm26ex4-cho005 の
  aliases に既に収まっており、submit 対象外（漏れではなく stale 除去）。
- converted 10,108 / rejects 2,227、重複0・漏れ0。ability_copy ギャップは
  残り0件でファミリー解消。

プロトテスト（test_vocab_pilot270.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
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


def _by_defn(e, zone, p):
    if zone == "bz":
        return {e.cdef(c).id: c for c in e.bz_tops(p)}
    return {e.cdef(c).id: c for c in e.zlist(zone, p)}


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in
                  (e.bz_tops(p) if zone == "bz" else e.zlist(zone, p)))


def _drive(e, stop, play=None, yes_no="yes", limit=1000):
    seen = []
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        seen.append(kind)
        if kind in ("charge", "main"):
            if kind == "main" and play is not None:
                ans = play(e, d, seen)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return seen
                    continue
            e.answer([keys.index("pass")])
        elif kind == "attack":
            e.answer([keys.index("pass")])
        elif kind == "block":
            e.answer([keys.index("no_block")] if "no_block" in keys
                     else list(range(d.get("min", 0))))
        elif kind == "choose_breaker":
            e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
        elif kind == "choose_shields":
            e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif kind == "declare_sback":
            e.answer([])
        elif kind == "yes_no":
            e.answer([keys.index(yes_no)])
        elif kind == "order_pending":
            e.answer([0])
        elif kind == "pay_mana":
            e.answer([0])
        elif kind == "choose_cards":
            e.answer(list(range(d.get("min", 0))))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if stop(e):
            return seen
    raise AssertionError("limit reached")


def _play_key(key, player=0):
    done = {}

    def play(e, d, seen):
        if e.s.active != player or done.get("opt"):
            return None
        keys = [o["key"] for o in d["options"]]
        if key in keys:
            done["opt"] = True
            return [keys.index(key)]
        return None
    return play


def _no_effect_tasks(e):
    return not any(t.get("t") == "effect" for t in e.s.tasks)


# ---------- 登録形 ----------

def test_registered_forms():
    c = _converted("dm26sd1-a005")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["name"] == "魔誕の斬将オルゲイト"
    assert c["types"] == ["creature"] and c["civs"] == ["water"]
    assert c["cost"] == 7 and c["power"] == 7000
    assert c["races"] == ["デーモン・コマンド"]
    assert c["keywords"] == ["hyper_energy", "blocker", "double_breaker"]
    assert c["source"]["aliases"] == ["dm24ex3-rp4s02", "dm24ex3-rp4sec03",
                                      "dm24rp4-s02", "dm24rp4-sec03", "dm25ex3-sp3"]
    assert c["abilities"] == [
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz", "subject": "self"},
         "effect": [{"op": "modify", "select": {"ref": "self"},
                     "mod": {"deny": ["be_chosen", "be_attacked"]},
                     "duration": "until_next_own_turn_start"}]},
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz", "subject": "self"},
         "effect": [{"op": "may", "body": [
             {"op": "move",
              "select": {"zone": "bz", "owner": "opp",
                         "filter": {"types": ["creature"]}, "count": 1},
              "to": "hand", "reason": "return"}]}]},
        {"kind": "trigger",
         "when": {"event": "trigger",
                  "subject": {"owner": "opp", "filter": {"types": ["creature"]}}},
         "if": {"is_turn": "opp"},
         "effect": [{"op": "may", "body": [{"op": "use_triggered_ability"}]}]},
    ]


def test_round305_no_rejects_left():
    """ability_copy ギャップは残り0件。n001 行も rejects から消えている。"""
    with pytest.raises(KeyError):
        _reject("dm26sd1-a005")
    with pytest.raises(KeyError):
        _reject("dm26sd1-n001")
    left = [json.loads(l)["id"] for l in open(REJECTS, encoding="utf-8")
            if "ability_copy" in (json.loads(l).get("gaps") or [])]
    assert left == []


# ---------- 実挙動（登録形） ----------

def test_registered_a005_copies_cip():
    """登録形のオルゲイトが、相手ターンの相手 CIP をコピーして1枚引く。"""
    e = _setup(load_rules(), {"hand": ["T748"], "mana": ["T001"] * 3},
               {"bz": ["dm26sd1-a005"]})
    play = _play_key("play:T748")

    def stop(ev):
        return (len(ev.zlist("hand", 1)) >= 1 and _no_effect_tasks(ev)
                and "T748" in _defns(ev, "bz", 0) and not ev.s.pending)

    seen = _drive(e, stop, play=play)
    assert len(e.zlist("hand", 0)) == 1   # 自分の CIP のドロー
    assert len(e.zlist("hand", 1)) == 2   # コピー1 + p1 のターンドロー1
    assert "yes_no" in seen


def test_registered_a005_cip_bounce():
    """登録形のオルゲイトが出た時、相手クリーチャーを手札に戻す。"""
    e = _setup(load_rules(), {"bz": ["T001"]},
               {"hand": ["dm26sd1-a005"], "mana": ["T003"] * 7})
    play = _play_key("play:dm26sd1-a005", player=1)

    def stop(ev):
        return ("T001" in _defns(ev, "hand", 0) and _no_effect_tasks(ev)
                and "dm26sd1-a005" in _defns(ev, "bz", 1))

    _drive(e, stop, play=play)
    assert "T001" in _defns(e, "hand", 0)
    assert "dm26sd1-a005" in _defns(e, "bz", 1)
