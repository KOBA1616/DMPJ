"""語彙パイロット第264弾のカード適用テスト（登録形）。

ラウンド299で trigger_doubling の6件のうち5件を新規登録、1件を差し戻し。
- 登録5件: dmrp04s-004（出た時・任意・ターン1回の2度トリガー）、dmrp21-013
  （タマシード出た時・ターン初回の2度トリガー）、dmrp22-040（呪文・攻撃
  トリガーの2度トリガー付与 end_of_turn）、dmex03-s02（出た時・対象
  アンタップ＋パワー3000、タップコストの任意2度トリガー）、
  dm24ex3-rp2s07（ハイパー時・攻撃トリガーの強制2度トリガー）。
- 差し戻し1件: dmrp12-008 → opt_reduce_then_entry_destroy（離脱型の
  2度トリガー＋W・ブレイカーは解決して partial に保存）。
- converted 10,086 / rejects 2,251、重複0・漏れ0。
"""
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


REGISTERED = ("dmrp04s-004", "dmrp21-013", "dmrp22-040", "dmex03-s02",
              "dm24ex3-rp2s07")


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


def _statics(card):
    return [ab for ab in card.get("abilities") or []
            if ab.get("kind") == "static"]


def _trigger_double(card):
    for ab in _statics(card):
        td = (ab.get("mod") or {}).get("trigger_double")
        if td is not None:
            return td
    return None


def test_registered_forms():
    for cid in REGISTERED:
        c = _converted(cid)
        parse_card(c, TABLES)
        assert c["source"]["review"] == "pending"
    # dmrp04s-004: 出た時・任意・ターン1回
    td = _trigger_double(_converted("dmrp04s-004"))
    assert td["may"] is True and td["once_per_turn"] is True
    assert td["source_subject"] is True
    assert td["when"] == {"event": "move", "to": "bz",
                          "subject": {"owner": "you",
                                      "filter": {"types": ["creature"]}}}
    # dmrp21-013: タマシード出た時・ターン初回
    td = _trigger_double(_converted("dmrp21-013"))
    assert td["first_per_turn"] is True and td["may"] is True
    assert td["when"]["subject"]["filter"] == {"types": ["tamaseed"],
                                               "civs": ["water"]}
    # dmrp22-040: 呪文・攻撃トリガーの2度トリガー付与
    c = _converted("dmrp22-040")
    grant = c["spell"][1]
    assert grant["op"] == "modify" and grant["duration"] == "end_of_turn"
    assert grant["mod"]["trigger_double"] == {
        "source_subject": True,
        "when": {"event": "attack", "subject": "self"}}
    # dmex03-s02: タップコストの任意2度トリガー
    td = _trigger_double(_converted("dmex03-s02"))
    assert td["may"] is True and td["cost"] == [
        {"op": "tap", "select": {"ref": "self"}}]
    assert td["when"]["subject"]["filter"] == {"types": ["creature"],
                                               "races": ["ジョーカーズ"]}
    assert td["when"]["subject"]["other"] is True
    # dm24ex3-rp2s07: ハイパー時・攻撃トリガーの強制2度トリガー
    td = _trigger_double(_converted("dm24ex3-rp2s07"))
    assert "may" not in td
    assert td["when"] == {"event": "attack",
                          "subject": {"owner": "you",
                                      "filter": {"types": ["creature"]}}}


def test_bounced_opt_reduce_then_entry_destroy():
    try:
        r = _reject("dmrp12-008")
    except KeyError:    # 後続の再変換で登録済みになった（rejects から外れた）
        assert _converted("dmrp12-008")
        return
    assert r["gaps"] == ["opt_reduce_then_entry_destroy"]
    p = r["partial"]
    assert p["keywords"] == ["double_breaker"]
    td = _trigger_double(p)
    assert td is not None
    assert td["when"] == {"event": "move", "from": "bz",
                          "subject": {"owner": "you",
                                      "filter": {"types": ["creature"]}}}
    assert p["source"]["unsupported"][0]["need"] == \
        "opt_reduce_then_entry_destroy"


def _hand_n(e, p=0):
    return len(e.zlist("hand", p))


def _drive(e, stop, choose=None, play=None, dbl=None, limit=800):
    """第264弾の汎用ドライバ（order_pending / choose_double_trigger 付き）。"""
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "order_pending":
            hit = next((i for i, k in enumerate(keys)
                        if k.startswith("pending:double_ask:")), None)
            e.answer([hit if hit is not None else 0])
            if stop(e):
                return
            continue
        if kind == "choose_double_trigger":
            ans = dbl(e, d) if dbl is not None else 0
            e.answer([ans])
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


def _play(defn, seen, max_n=1):
    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if f"play:{defn}" in keys and seen["n"] < max_n:
            seen["n"] += 1
            return [keys.index(f"play:{defn}")]
        return None
    return play


def test_004_doubles_entry_draw():
    """登録形 dmrp04s-004 がいれば T718 の出た時ドローが2度トリガーし、2枚引く。"""
    e = _setup(load_rules(), {"bz": ["dmrp04s-004"], "hand": ["T718"],
                               "mana": ["T718", "T718"]}, {})
    seen = {"n": 0}
    asks = {"n": 0}

    def dbl(e, d):
        asks["n"] += 1
        return 0   # はい

    _drive(e, lambda e: e.s.turn == 1 and seen["n"] == 1 and _hand_n(e) == 2,
           play=_play("T718", seen), dbl=dbl)
    assert asks["n"] == 1
    assert _hand_n(e) == 2   # 初期1枚 - 召喚1枚 + 出た時2枚
