"""語彙パイロット第282弾のカード適用テスト（登録形）。

ラウンド317で filter_same_name_as_event_card の純粋3件のうち2件を
新規登録、1件を差し戻し。
- dm24ex3-rp1s10 巨進の超人（召喚形）: partial の出た時能力
  （G・ストライク含む）はそのまま、召喚形の誘発を追加。
  alias: dm24ex3-rp1tr08 / dm24rp1-s10 / dm24rp1-tr08。
- dmrp02-006 サイバー・GG・ハルク（破壊形）: partial が無いため
  公式データ（水・コスト7・パワー8000・サイバー・コマンド）から
  全形を構築（キーワード blocker / double_breaker ＋ 誘発2つ）。
- c48-sec001 邪眼皇アレクサンドルIII世（詠唱形）は差し戻し:
  本印刷の本文形は第282弾の詠唱形イディオムで解決済み（解けた形は
  partial の abilities に格納）だが、submit は同一カードの最新版 ID
  でしか登録できない（load_rows の canonical_rows が古い印刷を
  落とす）。最新版 dm26ex4-cho010 は本文が異なる形（選んだ呪文を
  表向きにし、山札をシャッフルしてから唱える）で rejects に
  gaps [same_name_cast] で残存するため、本行のギャップを
  same_name_cast に精緻化して差し戻し、登録は最新版側の変換時に
  alias として畳み込む。別印刷 29-sec001 / dm29-s03 / dmc48-001 は
  converted に本誘発を欠いた形で登録済み（既存の欠落）。
  → ラウンド333で cho010 を新規登録し、c48-sec001 は alias として
  畳み込まれ、別印刷3件は CAST_FORM を足して是正された
  （test_c48_folded_into_cho010_round333 が現在の状態を固定する）。
converted 10,154 / rejects 2,179、重複0・漏れ0。
filter_same_name_as_event_card は残り0件で解消。

submit 後の照合（第313/315弾の教訓）: 登録2件とも登録形の abilities・
キーワードをテキストと照合し、partial の連結残り・テキスト由来の
追加は無いことを確認済み（本ファイルの test_registered_forms が固定）。

プロトテスト（test_vocab_pilot282.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine.scenario import build  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
IDS = ["dm24ex3-rp1s10", "dmrp02-006"]

CAST_FORM = {
    "kind": "trigger",
    "when": {"event": "cast", "player": "you", "from": ["hand", "graveyard"],
             "subject": {"filter": {"types": ["spell"],
                                    "civs": ["light", "water", "darkness"]}}},
    "if": {"exists": {"zone": "bz", "owner": "you", "other": True,
                      "filter": {"race_has": "ナイト"}}},
    "effect": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "look": True, "count": "all"},
         "as": "pile"},
        {"op": "choose",
         "select": {"ref": "pile",
                    "filter": {"name": {"name_of": "event.subject"},
                               "types": ["spell"]},
                    "count": 1},
         "as": "found"},
        {"op": "if", "cond": {"exists": {"ref": "found"}},
         "then": [{"op": "may",
                   "body": [{"op": "play_free", "select": {"ref": "found"}}]}]},
        {"op": "move", "select": {"ref": "pile", "count": "all"},
         "to": "deck", "reason": "put"},
        {"op": "shuffle", "player": "you"},
    ],
}

RP1_CIP = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [
        {"op": "move",
         "select": {"zone": "deck", "owner": "you", "from_top": 1},
         "to": "mana", "reason": "put", "tapped": True},
        {"op": "may",
         "body": [{"op": "move",
                   "select": {"zone": "mana", "owner": "you", "count": 1},
                   "to": "hand", "reason": "return"}]},
    ],
}

SUMMON_FORM = {
    "kind": "trigger", "once_per_turn": True,
    "when": {"event": "move", "to": "bz", "reason": "summon",
             "subject": {"owner": "you", "other": True,
                         "filter": {"types": ["creature"]}}},
    "effect": [
        {"op": "may",
         "body": [{"op": "play_free",
                   "select": {"zone": "mana", "owner": "you",
                              "filter": {"name": {"name_of": "event.subject"},
                                         "types": ["creature"]},
                              "count": 1}}]},
    ],
}

RP02_ABILITIES = [
    {
        "kind": "trigger",
        "when": {"event": "move", "to": "bz",
                 "subject": {"owner": "you", "other": True,
                             "filter": {"civs": ["water"], "types": ["creature"]}}},
        "effect": [{"op": "draw", "count": 1}],
    },
    {
        "kind": "trigger",
        "when": {"event": "move", "from": "bz", "to": "graveyard",
                 "reason": "destroy",
                 "subject": {"owner": "you",
                             "filter": {"civs": ["water"], "types": ["creature"]}}},
        "effect": [
            {"op": "may",
             "body": [{"op": "play_free",
                       "select": {"zone": "hand", "owner": "you",
                                  "filter": {"name": {"name_of": "event.subject"},
                                             "types": ["creature"]},
                                  "count": 1}}]},
        ],
    },
]

ABILITIES = {
    "dm24ex3-rp1s10": [RP1_CIP, SUMMON_FORM],
    "dmrp02-006": RP02_ABILITIES,
}

META = {
    "dm24ex3-rp1s10": ("巨進の超人", ["nature"], 4, 5000, ["ジャイアント"],
                       ["g_strike"],
                       ["dm24ex3-rp1tr08", "dm24rp1-s10", "dm24rp1-tr08"]),
    "dmrp02-006": ("サイバー・GG・ハルク", ["water"], 7, 8000,
                   ["サイバー・コマンド"], ["blocker", "double_breaker"], []),
}

TEXTS = {
    "dm24ex3-rp1s10":
        "{GS} G・ストライク\n"
        "このクリーチャーが出た時、自分の山札の上から１枚目をタップしてマナゾーンに置く。"
        "その後、カードを１枚、自分のマナゾーンから手札に戻してもよい。\n"
        "各ターンに一度、自分の他のクリーチャーが召喚によって出た時、それと同じ名前の"
        "クリーチャーを１体、自分のマナゾーンから出してもよい。",
    "dmrp02-006":
        "ブロッカーW・ブレイカー自分の他の水のクリーチャーがバトルゾーンに出た時、"
        "カードを１枚引く。このクリーチャーまたは自分の他の水のクリーチャーが"
        "破壊された時、それと同じ名前のクリーチャーを１体、自分の手札から"
        "バトルゾーンに出してもよい。",
}


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


def _setup(p0, p1=None):
    return build(load_rules(), {"p0": p0, "p1": p1 or {"bz": ["T001"]},
                                "filler": "T001", "seed": 1, "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """第281弾 cards テストの汎用ドライバ（モードなし版）。"""

    def __init__(self, play=None, choose=None):
        self.play = play
        self.choose = choose
        self.seen = []

    def run(self, e, stop, limit=800):
        for _ in range(limit):
            d = e.advance()
            assert d is not None, "game ended"
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
            self.seen.append(kind)
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
    seen = {"n": 0}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and seen["n"] < 1:
            seen["n"] += 1
            return [keys.index(key)]
        return None

    return play


def _choose_targets(*defns):
    queue = list(defns)

    def choose(e, d):
        if not queue:
            return None
        for i, o in enumerate(d["options"]):
            if e.cdef(o["cid"]).id == queue[0]:
                queue.pop(0)
                return [i]
        return None

    return choose


# ---------- 登録形 ----------

def test_registered_forms():
    for cid in IDS:
        c = _converted(cid)
        parse_card(json.loads(json.dumps(c)), TABLES)
        assert "unsupported" not in (c.get("source") or {}), cid
        try:
            _reject(cid)
            raise AssertionError(f"{cid} が rejects に残っている")
        except KeyError:
            pass
        name, civs, cost, power, races, keywords, aliases = META[cid]
        assert c["name"] == name and c["civs"] == civs, cid
        assert c["types"] == ["creature"] and c["cost"] == cost, cid
        assert c["power"] == power and c["races"] == races, cid
        assert c.get("keywords") == keywords, cid
        if aliases:
            assert sorted(c["source"]["aliases"]) == sorted(aliases), cid
        else:
            assert not (c.get("source") or {}).get("aliases"), cid
        assert c["text"] == TEXTS[cid], cid
        # abilities は登録形と完全一致（partial の連結残り・追加なし）
        assert c["abilities"] == ABILITIES[cid], cid


def test_c48_folded_into_cho010_round333():
    """c48-sec001 はラウンド333で dm26ex4-cho010 の登録時に alias
    として畳み込まれた（独立エントリではなく、reject 行も残らない）。
    same_name_cast / filter_same_name_as_event_card の行は残り0件。
    （ラウンド317時点では gaps [same_name_cast] で差し戻され、解けた
    詠唱形は partial の abilities に銀行されていた。）"""
    try:
        _converted("c48-sec001")
        raise AssertionError("c48-sec001 が独立エントリとして登録されている")
    except KeyError:
        pass
    cho = _converted("dm26ex4-cho010")
    aliases = (cho.get("source") or {}).get("aliases") or []
    assert "c48-sec001" in aliases
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            assert r["id"] not in ("c48-sec001", "dm26ex4-cho010"), r["id"]
            assert "same_name_cast" not in (r.get("gaps") or []), r["id"]
            assert "filter_same_name_as_event_card" not in (r.get("gaps") or []), r["id"]


# ---------- 実挙動: dm24ex3-rp1s10（登録形・召喚形） ----------

def test_registered_rp1s10_summon_form():
    """自分の他のクリーチャー（T802）が召喚によって出た時、それと
    同じ名前のクリーチャー（マナゾーンの T802）を出せる（may 受諾）。"""
    e = _setup({"bz": ["dm24ex3-rp1s10"], "hand": ["T802"],
                "mana": ["T802", "T001", "T001", "T001"]})
    drv = _Driver(play=_play_once("play:T802"))
    drv.run(e, lambda ev: _defns(ev, "bz", 0) == ["T802", "T802", "dm24ex3-rp1s10"]
            and _quiet(ev))
    assert _defns(e, "bz", 0).count("T802") == 2


# ---------- 実挙動: dmrp02-006（登録形） ----------

def test_registered_rp02_draw_on_ally_entry():
    """自分の他の水のクリーチャー（T030）が出た時、カードを1枚引く。"""
    # T030 は光/水の多色: 支払いには光と水の両方のマナが要る
    e = _setup({"bz": ["dmrp02-006"], "hand": ["T030"],
                "mana": ["T010", "T030", "T001", "T001"]})
    drv = _Driver(play=_play_once("play:T030"))
    drv.run(e, lambda ev: "T030" in _defns(ev, "bz", 0)
            and len(ev.zlist("hand", 0)) == 1 and _quiet(ev))
    assert _defns(e, "hand", 0) == ["T001"]


def test_registered_rp02_destroy_form():
    """このクリーチャーが破壊された時、手札の同じ名前のクリーチャーを
    バトルゾーンに出せる（may 受諾）。破壊された1枚は墓地に残る。"""
    e = _setup({"bz": ["dmrp02-006"], "hand": ["dmrp02-006"]},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"),
                  choose=_choose_targets("dmrp02-006"))
    drv.run(e, lambda ev: "dmrp02-006" in _defns(ev, "bz", 0)
            and "dmrp02-006" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert _defns(e, "graveyard", 0) == ["dmrp02-006"]
    assert _defns(e, "bz", 0).count("dmrp02-006") == 1
