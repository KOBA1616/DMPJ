"""語彙パイロット第272弾のカード適用テスト（登録形）。

ラウンド307で infinite_power / infinite_breaker の9件を再変換。
- 新規登録5件: dm26ex3-079、dmr10-015、dm26ex3-054、dmex08-216、dmsp02-009。
- 差し戻し3件（解けた条項は partial に bank）:
  dm26rp2-s011 → trigger_when_opponent_plays_without_paying +
  deck_faceup_power（バトル中パワー∞は battle_power で bank）／
  dm26rp3-td001・dmart26-002 → ignore_abilities（∞ブレイカーは bank）。
- dm25bd2-007 は partial が無く、コスト・パワーとも印刷∞
  （infinite_cost_power 自体）で placeholder を置けないため手つかず。
- converted 10,115 → 10,120 / rejects 2,218 → 2,213、重複0・漏れ0。
- 付随修復: dm26ex4-054 に混入していた dm26ex3-054 の aliases を除去し、
  dm26ex3-054 側に登録した。dm26ex3-079 は submit がテキスト由来の
  CIP discard を重複登録したため同一誘発を1件除去した。

プロトテスト（test_vocab_pilot272.py）とは別プロセスで実行すること
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
INF = 1073741824


def _setup(rules, p0, p1=None):
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


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in
                  (e.bz_tops(p) if zone == "bz" else e.zlist(zone, p)))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "janken", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """第271弾のドライバ＋ブレイク数・ブロックの台本。"""

    def __init__(self, play=None, choose=None, yes_no="yes", attack=None,
                 charge=None, breaker=None, block=None):
        self.play = play
        self.choose = choose
        self.yes_no = yes_no
        self.attack = attack
        self.charge = charge
        self.breaker = breaker
        self.block = block
        self.seen_kinds = []

    def run(self, e, stop, limit=800):
        for _ in range(limit):
            d = e.advance()
            assert d is not None, "game ended"
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
            self.seen_kinds.append(kind)
            if kind == "choose_cards" and self.choose is not None:
                ans = self.choose(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "main" and self.play is not None:
                ans = self.play(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "charge" and self.charge is not None:
                ans = self.charge(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "attack" and self.attack is not None:
                ans = self.attack(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "choose_breaker" and self.breaker is not None:
                ans = self.breaker(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "block" and self.block is not None:
                ans = self.block(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "declare_strigger":
                e.answer([])
            elif kind == "declare_sback":
                e.answer([])
            elif kind == "choose_breaker":
                e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
            elif kind == "choose_shields":
                e.answer(list(range(d.get("min", 0))))
            elif kind == "pay_mana":
                e.answer([0])
            elif kind == "yes_no":
                want = "yes" if self.yes_no == "yes" else "no"
                e.answer([keys.index(want)])
            elif kind == "order_pending":
                e.answer([0])
            elif kind == "block":
                if "no_block" in keys:
                    e.answer([keys.index("no_block")])
                else:
                    e.answer(list(range(d.get("min", 0))))
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
            if stop(e):
                return
        raise AssertionError("limit reached")


def _play_once(key):
    seen = {}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and not seen.get("opt"):
            seen["opt"] = True
            return [keys.index(key)]
        return None

    return play


def _attack_once(key):
    seen = {}

    def attack(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and not seen.get("opt"):
            seen["opt"] = True
            return [keys.index(key)]
        return None

    return attack


def _break_n(n):
    def breaker(e, d):
        keys = [o["key"] for o in d["options"]]
        hit = [i for i, k in enumerate(keys) if k.split(":")[-1] == str(n)]
        return [hit[0]] if hit else None

    return breaker


def _block_with(defn):
    def block(e, d):
        keys = [o["key"] for o in d["options"]]
        hit = [i for i, k in enumerate(keys) if defn in k]
        return [hit[0]] if hit else None

    return block


# ---------- 登録形 ----------

def test_round307_registered_forms():
    for cid in ("dm26ex3-079", "dmr10-015", "dm26ex3-054", "dmex08-216",
                "dmsp02-009"):
        parse_card(copy.deepcopy(_converted(cid)), TABLES)

    c = _converted("dmr10-015")
    assert c["keywords"] == ["infinite_breaker"]
    assert c["source"]["aliases"] == ["dmr10-015m"]

    c = _converted("dmsp02-009")
    assert "infinite_power_attacker" in c["keywords"]

    # submit のテキスト由来マージで重複した CIP discard は除去済み（2能力のみ）
    c = _converted("dm26ex3-079")
    assert len(c["abilities"]) == 2
    cip, atk = c["abilities"]
    assert cip["when"] == {"event": "move", "to": "bz", "subject": "self"}
    assert cip["effect"] == [{"op": "discard", "select": {
        "zone": "hand", "owner": "opp", "count": 5, "chooser": "opp"}}]
    assert atk["when"] == {"event": "attack", "subject": "self"}
    assert atk["effect"][0]["mod"] == {"power_set": -INF}

    c = _converted("dm26ex3-054")
    assert c["power"] == INF  # 印刷パワー∞（登録時に欠落していたものを補った）
    assert len(c["abilities"]) == 1
    assert c["abilities"][0]["effect"][0]["mod"] == {"power_set": -INF}
    assert c["source"]["aliases"] == ["dm26ex3-sec016", "dm26ex3-sec016cho",
                                      "promoy25-107"]

    c = _converted("dmex08-216")
    mod = c["spell"][0]["mod"]
    assert mod["grant"] == ["infinite_power_attacker", "infinite_breaker"]
    assert mod["gain"][0]["when"] == {"event": "battle_win", "subject": "self"}

    # 付随修復: dm26ex4-054 は帝王坂の aliases をもう名乗らない
    c = _converted("dm26ex4-054")
    assert "aliases" not in (c.get("source") or {})
    assert "keywords" not in c


def test_round307_bounces_banked():
    r = _reject("dm26rp2-s011")
    assert r["gaps"] == ["trigger_when_opponent_plays_without_paying",
                         "deck_faceup_power"]
    statics = [a for a in r["partial"]["abilities"] if a["kind"] == "static"]
    assert statics[-1]["mod"] == {"battle_power": {"amount": INF}}

    for cid in ("dm26rp3-td001", "dmart26-002"):
        r = _reject(cid)
        assert r["gaps"] == ["ignore_abilities"]
        assert "infinite_breaker" in r["partial"]["keywords"]

    r = _reject("dm25bd2-007")
    assert r["gaps"] == ["infinite_cost_power", "infinite_breaker"]
    assert not r.get("partial")


# ---------- 実挙動 ----------

def test_registered_dmr10_015_infinite_breaker_chooses_two():
    """∞ブレイカー: 好きな数（ここでは2つ）を選んでブレイクする。"""
    e = _setup(load_rules(), {"bz": ["dmr10-015"]}, {})
    drv = _Driver(attack=_attack_once("attack:dmr10-015:player"),
                  breaker=_break_n(2))
    drv.run(e, lambda ev: len(ev.zlist("shield", 1)) == 3 and _quiet(ev))
    assert len(e.zlist("shield", 1)) == 3


def test_registered_dmsp02_009_infinite_power_beats_giant_and_breaks():
    """∞パワーアタッカー: パワー99999のブロッカーに勝ち、勝利時1ブレイク。"""
    e = _setup(load_rules(), {"bz": ["dmsp02-009"]}, {"bz": ["T763"]})
    drv = _Driver(attack=_attack_once("attack:dmsp02-009:player"),
                  block=_block_with("T763"))
    drv.run(e, lambda ev: "T763" in _defns(ev, "graveyard", 1)
            and len(ev.zlist("shield", 1)) == 4 and _quiet(ev))
    assert "T763" in _defns(e, "graveyard", 1)
    assert "dmsp02-009" in _defns(e, "bz", 0)
    assert len(e.zlist("shield", 1)) == 4


def test_registered_dm26ex3_079_entry_opponent_discards_five():
    """出た時: 相手は自身の手札を5枚選んで捨てる（chooser: opp）。"""
    e = _setup(load_rules(),
               {"hand": ["dm26ex3-079"],
                "mana": ["T010", "T008"] + ["T001"] * 6},
               {"hand": ["T001", "T002", "T003", "T004", "T005", "T007"]})
    drv = _Driver(play=_play_once("play:dm26ex3-079"))
    drv.run(e, lambda ev: len(ev.zlist("graveyard", 1)) == 5 and _quiet(ev))
    assert len(e.zlist("graveyard", 1)) == 5
    # 手札6枚から5枚捨てて残り1枚＋相手ターン開始時のドロー1枚
    assert len(e.zlist("hand", 1)) == 2
    assert "dm26ex3-079" in _defns(e, "bz", 0)


def test_registered_dm26ex3_054_entry_power_minus_infinite():
    """出た時: 相手クリーチャー1体のパワーを－∞し、パワー0以下で破壊される。"""
    e = _setup(load_rules(),
               {"hand": ["dm26ex3-054"], "mana": ["T008"] * 8},
               {"bz": ["T763"]})
    drv = _Driver(play=_play_once("play:dm26ex3-054"))
    drv.run(e, lambda ev: "T763" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T763" in _defns(e, "graveyard", 1)
    assert "dm26ex3-054" in _defns(e, "bz", 0)


def test_registered_dmex08_216_grants_infinite_keywords():
    """呪文で付与した ∞パワーアタッカー＋∞ブレイカーで2ブレイク選べる。"""
    e = _setup(load_rules(),
               {"hand": ["dmex08-216"], "mana": ["T034"] * 13, "bz": ["T001"]},
               {})
    drv = _Driver(play=_play_once("play:dmex08-216"),
                  attack=_attack_once("attack:T001:player"),
                  breaker=_break_n(2))
    drv.run(e, lambda ev: len(ev.zlist("shield", 1)) == 3 and _quiet(ev))
    assert len(e.zlist("shield", 1)) == 3
