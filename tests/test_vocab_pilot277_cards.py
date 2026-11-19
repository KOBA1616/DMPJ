"""語彙パイロット第277弾のカード適用テスト（登録形）。

ラウンド312で true_escape の純粋3件をすべて新規登録、差し戻しなし。
- dm23rp2x-010 アウルーリー-T8（光・コスト5・パワー6000・メカ・デル・
  ディネロ）: partial はキーワードのみ。true_escape をキーワードに足し、
  「自分のシールドがなければ、このクリーチャーは離れない」を常在型
  {affects: self, if: {not: {exists: {zone: shield, owner: you}}},
  mod: {no_leave: true}} で組んだ（プロト T786 と同形）。
  alias: dm23rp2-010 / promoy22-019。
- dm24bd5-004 聖霊妖精オーデマリー（光・コスト5・パワー6000）:
  partial は abilities 空。出た時・攻撃する時の「上から2枚を見て1枚を
  シールド化・残りを手札」（choose {from_top: 2, look: true, count: all}
  as: pile → 1枚を shield へ → 残りを hand へ、2誘発）と、シールド
  ゾーンのスノーフェアリーすべてへの S・トリガー付与常在型
  {affects: {zone: shield, owner: you, filter: {race_has: スノー
  フェアリー}}, mod: {grant: [s_trigger]}}（dm24ex1-001 先例形）を
  公式全文から組んだ。alias: promoy24-037。
- dm24rp1-011 獲銀月 ミール（光・コスト4・パワー5000・ハイパー化）:
  partial のハイパー静的は完全。真・エスケープはハイパー時のみのため、
  キーワード本体を mod.gain で {hyper: true} ゲートした常在型を1つ
  追加した（mod grant は置換能力を届けない。第240弾の静的 gain 展開）。
  alias: dm24rp1-sec13。
- converted 10,138 / rejects 2,195、重複0・漏れ0。true_escape ギャップは
  残り0件でファミリー解消。

プロトテスト（test_vocab_pilot277.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
"""
import copy
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.scenario import build  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
IDS = ["dm23rp2x-010", "dm24bd5-004", "dm24rp1-011"]

TRUE_ESCAPE_AB = {
    "kind": "replace", "optional": True,
    "when": {"event": "move", "from": "bz", "subject": "self"},
    "if": {"cmp": [{"count": {"zone": "shield", "owner": "you"}}, ">=", 2]},
    "instead": [{"op": "move",
                 "select": {"zone": "shield", "owner": "you", "count": 2},
                 "to": "hand", "reason": "return", "strigger": "off"}],
}

NO_LEAVE_STATIC = {
    "kind": "static", "affects": "self",
    "if": {"not": {"exists": {"zone": "shield", "owner": "you"}}},
    "mod": {"no_leave": True},
}

LOOK2_EFFECT = [
    {"op": "choose",
     "select": {"zone": "deck", "owner": "you", "from_top": 2, "look": True,
                "count": "all"},
     "as": "pile"},
    {"op": "move", "select": {"ref": "pile", "count": 1},
     "to": "shield", "reason": "put"},
    {"op": "move", "select": {"ref": "pile", "count": "all"},
     "to": "hand", "reason": "draw"},
]


def _setup(rules, p0, p1=None, **kw):
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": "T001",
                         "seed": 1, "deck_size": 20, **kw})


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject(cid):
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            if r["id"] == cid:
                return r
    raise KeyError(cid)


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """汎用ドライバ（第276弾 cards のものに置換ポリシーとハイパー解放を追加）。

    play: main 決定で (e, d) -> 答えのリストか None を返すフック。
    hyper: その defn の hyper: キーが main に現れたら一度だけ解放する。
    choose: choose_cards へのフック (e, d) -> 答えのリストか None。
    replace: choose_replacement で "accept" なら replace: を、"decline"
    なら decline を選ぶ。seen に全決定種別を記録する。
    """

    def __init__(self, play=None, hyper=None, choose=None, replace="accept"):
        self.play = play
        self.hyper = hyper
        self.hyper_done = False
        self.choose = choose
        self.replace = replace
        self.seen = []

    def run(self, e, stop, limit=1200):
        for _ in range(limit):
            d = e.advance()
            assert d is not None, "game ended"
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
            self.seen.append(kind)
            if kind == "choose_replacement":
                if self.replace == "accept":
                    hit = [i for i, k in enumerate(keys) if k.startswith("replace:")]
                    assert hit, "置換の諮問に replace 選択肢が無い"
                    e.answer(hit[:1])
                else:
                    e.answer([keys.index("decline")])
                if stop(e):
                    return
                continue
            if kind == "choose_cards" and self.choose is not None:
                ans = self.choose(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "main" and self.hyper is not None and not self.hyper_done:
                key = f"hyper:{self.hyper}"
                if key in keys:
                    self.hyper_done = True
                    e.answer([keys.index(key)])
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
                e.answer([keys.index("yes")])
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


# ---------- 登録形 ----------

def test_registered_forms():
    for cid in IDS:
        c = _converted(cid)
        parse_card(copy.deepcopy(c), TABLES)
        assert "unsupported" not in (c.get("source") or {}), cid
        try:
            _reject(cid)
            raise AssertionError(f"{cid} が rejects に残っている")
        except KeyError:
            pass

    c = _converted("dm23rp2x-010")
    assert c["name"] == "アウルーリー-T8"
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 5 and c["power"] == 6000
    assert c["races"] == ["メカ・デル・ディネロ"]
    assert c["keywords"] == ["blocker", "double_breaker", "true_escape"]
    assert c["source"]["aliases"] == ["dm23rp2-010", "promoy22-019"]
    assert c["abilities"] == [NO_LEAVE_STATIC]
    assert c["text"] == (
        "ブロッカー（このクリーチャーをタップして、相手クリーチャーの攻撃先を"
        "このクリーチャーに変更してもよい）\n"
        "W・ブレイカー（このクリーチャーはシールドを２つブレイクする）\n"
        "真・エスケープ（このクリーチャーが離れる時、かわりに自分のシールドを"
        "２つ手札に加えてもよい。ただし、その「S・トリガー」は使えない）\n"
        "自分のシールドがなければ、このクリーチャーは離れない。")

    c = _converted("dm24bd5-004")
    assert c["name"] == "聖霊妖精オーデマリー"
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 5 and c["power"] == 6000
    assert c["races"] == ["スノーフェアリー", "エンジェル・コマンド"]
    assert c["keywords"] == ["double_breaker", "true_escape"]
    assert c["source"]["aliases"] == ["promoy24-037"]
    trig_in, trig_atk, grant = c["abilities"]
    assert trig_in == {"kind": "trigger",
                       "when": {"event": "move", "to": "bz", "subject": "self"},
                       "effect": LOOK2_EFFECT}
    assert trig_atk == {"kind": "trigger",
                        "when": {"event": "attack", "subject": "self"},
                        "effect": LOOK2_EFFECT}
    assert grant == {"kind": "static",
                     "affects": {"zone": "shield", "owner": "you",
                                 "filter": {"race_has": "スノーフェアリー"}},
                     "mod": {"grant": ["s_trigger"]}}

    c = _converted("dm24rp1-011")
    assert c["name"] == "獲銀月 ミール"
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 4 and c["power"] == 5000
    assert c["races"] == ["イニシエート", "超化獣"]
    assert c["keywords"] == ["blocker"] and c["hyper"] is True
    assert c["source"]["aliases"] == ["dm24rp1-sec13"]
    assert len(c["abilities"]) == 4
    gain = c["abilities"][3]
    assert gain == {"kind": "static", "affects": "self", "if": {"hyper": True},
                    "mod": {"gain": [TRUE_ESCAPE_AB]}}


# ---------- 実挙動 ----------

def test_registered_010_destroy_replaced():
    """dm23rp2x-010: 破壊される時、シールド2枚を手札に加えて残る。"""
    e = _setup(load_rules(),
               {"bz": ["dm23rp2x-010"]},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"))
    drv.run(e, lambda ev: "dm23rp2x-010" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 3 and _quiet(ev))
    assert "dm23rp2x-010" in _defns(e, "bz", 0)
    assert "dm23rp2x-010" not in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == 3
    # 手札3枚 = 支払ったシールド2枚＋次の自分のターンのドロー1枚
    assert _defns(e, "hand", 0) == ["T001", "T001", "T001"]
    assert drv.seen.count("choose_replacement") == 1


def test_registered_010_no_leave_without_shields():
    """dm23rp2x-010: シールドがなければ離れない（破壊呪文でも残る）。"""
    e = _setup(load_rules(),
               {"bz": ["dm23rp2x-010"], "shield": []},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"))
    drv.run(e, lambda ev: "T056" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "dm23rp2x-010" in _defns(e, "bz", 0)
    assert "dm23rp2x-010" not in _defns(e, "graveyard", 0)
    assert "choose_replacement" not in drv.seen


def test_registered_004_entry_trigger_and_shield_grant():
    """dm24bd5-004: 出た時、上から2枚のうち1枚がシールド化・残りが手札へ。
    シールドゾーンのスノーフェアリー（同名コピー）は S・トリガーを得る。"""
    e = _setup(load_rules(),
               {"hand": ["dm24bd5-004"], "mana": ["T030"] * 5,
                "shield": ["dm24bd5-004", "T001", "T001", "T001", "T001"]},
               {"bz": ["T001"]})
    shield_copy = next(c for c in e.zlist("shield", 0)
                       if e.cdef(c).id == "dm24bd5-004")
    captured = {}

    def play(ev, d):
        keys = [o["key"] for o in d["options"]]
        if "play:dm24bd5-004" in keys and "top2" not in captured:
            captured["top2"] = list(ev.zlist("deck", 0)[:2])   # 上から2枚（実体）
            captured["deck_n"] = len(ev.zlist("deck", 0))
            return [keys.index("play:dm24bd5-004")]
        return None

    drv = _Driver(play=play)
    drv.run(e, lambda ev: "dm24bd5-004" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 6 and _quiet(ev))
    top2 = captured["top2"]
    assert len(e.zlist("deck", 0)) == captured["deck_n"] - 2
    zones = sorted(e.s.cards[c].zone for c in top2)
    assert zones == ["hand", "shield"]   # 1枚シールド化・残りを手札に加えた
    assert "s_trigger" in e.chars_ro(shield_copy)["keywords"]


def _choose_meal_or_t001(e, d):
    """T056 の対象は dm24rp1-011、ハイパー解放のコストは T001 を選ぶ。

    置換の支払い（シールド2枚の choose）には触らないよう、選択肢がすべて
    バトルゾーンの時だけ応じる。"""
    if not all(e.s.cards[o["cid"]].zone == "bz" for o in d["options"]):
        return None
    defns = [e.cdef(o["cid"]).id for o in d["options"]]
    for want in ("dm24rp1-011", "T001"):
        if want in defns:
            return [defns.index(want)]
    return None


def test_registered_011_hyper_true_escape():
    """dm24rp1-011: ハイパー化中は真・エスケープが働く（mod.gain 展開）。"""
    e = _setup(load_rules(),
               {"bz": ["dm24rp1-011", "T001"]},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"), hyper="dm24rp1-011",
                  choose=_choose_meal_or_t001)
    drv.run(e, lambda ev: "dm24rp1-011" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 3 and _quiet(ev))
    assert drv.hyper_done   # ハイパー解放した（コストの T001 はターン3開始で起き直す）
    assert "dm24rp1-011" in _defns(e, "bz", 0)
    assert "dm24rp1-011" not in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == 3            # 2枚払って残った
    assert drv.seen.count("choose_replacement") == 1


def test_registered_011_without_hyper_destroyed():
    """dm24rp1-011: ハイパー化していなければ真・エスケープは働かない。"""
    e = _setup(load_rules(),
               {"bz": ["dm24rp1-011", "T001"]},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"), choose=_choose_meal_or_t001)
    drv.run(e, lambda ev: "dm24rp1-011" in _defns(ev, "graveyard", 0)
            and _quiet(ev))
    assert "dm24rp1-011" in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == 5
    assert "choose_replacement" not in drv.seen
