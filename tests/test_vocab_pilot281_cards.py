"""語彙パイロット第281弾のカード適用テスト（登録形）。

ラウンド316で leave_replacement_shield_to_hand の純粋3件をすべて
新規登録、差し戻しなし。関連する単独行 dm26rp3-001
（once_per_turn_leave_replacement_shield_to_hand）も、出た時のモード
能力を公式全文から構築して併せて新規登録した（計4件）。
- dm23ex3-tf03 「終焉」の頂 オーエン・ザ・ロード（基本形・2枚）
  ※ partial に欠けていた出た時能力（召喚によって出た時: 墓地のカードを
  すべて山札に加えてシャッフル＋上から3枚をシールド化してもよい）を
  公式全文から構築した。alias: dmbd06-001。
- dm24ex4-042 星姫械 エルナドンナ（他者・各ターン一度形・1枚）
  alias: dm23rp4-012 / dm23rp4x-012 / dm24ex4-pr002。
- dmx23-025 若き日の族長 ヘンザ（基本形・2枚、革命チェンジは partial のまま）
- dm26rp3-001 ヒトリダチ ケントナーク（各ターンに1度・ジョーカーズ形・1枚）
  ※ 出た時のモード能力（シールド化／Jビッグ1＝use_cip、dm26rp3-077 の
  登録先例形）を公式全文から構築した。置換の subject は原文が
  「自分のジョーカーズ」（クリーチャー限定なし）のため filter は
  race_has: ジョーカーズ のみ（types: [creature] を付けない）。
alias はいずれも canonical の source.aliases に畳み込まれ、rejects に
alias 行は無かったため stale 整理なし。
converted 10,152 / rejects 2,181、重複0・漏れ0。
leave_replacement_shield_to_hand と
once_per_turn_leave_replacement_shield_to_hand は残り0件で解消。

submit 後の照合（第313/315弾の教訓）: 4件とも登録形の abilities・
キーワードをテキストと照合し、partial の連結残り・テキスト由来の
追加は無いことを確認済み（本ファイルの test_registered_forms が固定）。

プロトテスト（test_vocab_pilot281.py）とは別プロセスで実行すること
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
IDS = ["dm23ex3-tf03", "dm24ex4-042", "dmx23-025", "dm26rp3-001"]

BASIC_FORM = {
    "kind": "replace", "optional": True,
    "when": {"event": "move", "from": "bz",
             "subject": {"owner": "you", "filter": {"types": ["creature"]}}},
    "if": {"cmp": [{"count": {"zone": "shield", "owner": "you"}}, ">=", 2]},
    "instead": [{"op": "move",
                 "select": {"zone": "shield", "owner": "you", "count": 2},
                 "to": "hand", "reason": "return", "strigger": "off"}],
}

OTHER_ONCE_FORM = {
    "kind": "replace", "optional": True, "once_per_turn": True,
    "when": {"event": "move", "from": "bz",
             "subject": {"owner": "you", "other": True,
                         "filter": {"types": ["creature"]}}},
    "if": {"cmp": [{"count": {"zone": "shield", "owner": "you"}}, ">=", 1]},
    "instead": [{"op": "move",
                 "select": {"zone": "shield", "owner": "you", "count": 1},
                 "to": "hand", "reason": "return", "strigger": "off"}],
}

TF03_CIP = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self", "reason": "summon"},
    "effect": [
        {"op": "move", "select": {"zone": "graveyard", "owner": "you", "count": "all"},
         "to": "deck", "reason": "return"},
        {"op": "shuffle", "player": "you"},
        {"op": "may", "body": [
            {"op": "move", "select": {"zone": "deck", "owner": "you", "from_top": 3},
             "to": "shield", "reason": "charge"}]}],
}

RP3_CIP = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [
        {"op": "modal", "modes": [
            [{"op": "move", "select": {"zone": "deck", "owner": "you", "from_top": 1},
              "to": "shield", "reason": "charge"}],
            [{"op": "use_cip",
              "select": {"zone": "bz", "owner": "you", "other": True, "count": 1,
                         "filter": {"race_has": "ジョーカーズ"}}}]]}],
}

RP3_FORM = {
    "kind": "replace", "optional": True, "once_per_turn": True,
    "when": {"event": "move", "from": "bz",
             "subject": {"owner": "you", "filter": {"race_has": "ジョーカーズ"}}},
    "if": {"cmp": [{"count": {"zone": "shield", "owner": "you"}}, ">=", 1]},
    "instead": [{"op": "move",
                 "select": {"zone": "shield", "owner": "you", "count": 1},
                 "to": "hand", "reason": "return", "strigger": "off"}],
}

HENZA_DECLARE = {
    "kind": "declare", "zone": "hand",
    "when": {"event": "attack",
             "subject": {"owner": "you",
                         "filter": {"civs": ["light", "nature"], "cost_ge": 5,
                                    "race_has": "ドラゴン"}}},
    "effect": [{"op": "swap", "out": {"ref": "event.subject"},
                "in": {"ref": "self"}}],
}

ABILITIES = {
    "dm23ex3-tf03": [TF03_CIP, BASIC_FORM],
    "dm24ex4-042": [OTHER_ONCE_FORM],
    "dmx23-025": [HENZA_DECLARE, BASIC_FORM],
    "dm26rp3-001": [RP3_CIP, RP3_FORM],
}

META = {
    "dm23ex3-tf03": ("「終焉」の頂 オーエン・ザ・ロード", ["light"], 11, 11500,
                     ["デーモン・コマンド", "アンノウン", "ゼニス"],
                     ["blocker", "double_breaker"], ["dmbd06-001"]),
    "dm24ex4-042": ("星姫械 エルナドンナ", ["light"], 2, 2500,
                    ["メカ・デル・ステラ"], ["blocker"],
                    ["dm23rp4-012", "dm23rp4x-012", "dm24ex4-pr002"]),
    "dmx23-025": ("若き日の族長 ヘンザ", ["light", "nature"], 8, 11500,
                  ["ジュラシック・コマンド・ドラゴン", "革命軍", "ダママ団"],
                  ["double_breaker"], []),
    "dm26rp3-001": ("ヒトリダチ ケントナーク", ["light"], 4, 4500,
                    ["ジョーカーズ"], ["blocker"], []),
}

TEXTS = {
    "dm23ex3-tf03":
        "ブロッカー\nW・ブレイカー\n"
        "このクリーチャーが召喚によって出た時、自分の墓地のカードをすべて山札に加えてシャッフルする。"
        "その後、自分の山札の上から３枚をシールド化してもよい。\n"
        "自分のクリーチャーが離れる時、かわりに自分のシールドを２つ、手札に戻してもよい。"
        "ただし、その「S・トリガー」は使えない。",
    "dm24ex4-042":
        "ブロッカー\n"
        "各ターンに一度、自分の他のクリーチャーが離れる時、かわりに自分のシールドを１つ手札に加えてもよい。"
        "ただし、その「S・トリガー」は使えない。",
    "dmx23-025":
        "マナゾーンに置く時、このカードはタップして置く。"
        "革命チェンジ：光または自然のコスト５以上のドラゴン（自分の光または自然のコスト５以上のドラゴンが"
        "攻撃する時、そのクリーチャーと手札にあるこのクリーチャーを入れ替えてもよい）"
        "W・ブレイカー自分のクリーチャーがバトルゾーンを離れる時、かわりに自分のシールドを２つ手札に"
        "戻してもよい。ただし、その「S・トリガー」は使えない。",
    "dm26rp3-001":
        "ブロッカー\nこのクリーチャーが出た時、次の中から１回選ぶ。\n"
        "▶自分の山札の上から１枚をシールド化する。\n"
        "▶Jビッグ１する。（自分の他のジョーカーズの、Jビッグ１以外の、出た時にトリガーする能力を１つ使う）\n"
        "各ターンに１度、自分のジョーカーズが離れる時、かわりに自分のシールドを１つ手札に加えてもよい。"
        "その「S・トリガー」は使えない。",
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
    """第281弾本体の汎用ドライバに choose_mode（モード列）を足したもの。"""

    def __init__(self, play=None, replace="accept", choose=None, modes=None):
        self.play = play
        self.replace = replace
        self.choose = choose
        self.modes = list(modes or [])
        self.seen = []

    def run(self, e, stop, limit=800):
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
            if kind == "choose_mode" and self.modes:
                want = f"mode:{self.modes.pop(0)}"
                assert want in keys, (want, keys)
                e.answer([keys.index(want)])
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


def _play_times(key, times):
    seen = {"n": 0}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and seen["n"] < times:
            seen["n"] += 1
            return [keys.index(key)]
        return None

    return play


def _play_once(key):
    return _play_times(key, 1)


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


# ---------- 実挙動: dm23ex3-tf03（登録形） ----------

def test_registered_tf03_cip_on_summon():
    """召喚して出た時: 墓地のカードがすべて山札に加わり（シャッフル）、
    その後上から3枚がシールド化される（may を受諾）。"""
    e = _setup({"hand": ["dm23ex3-tf03"], "mana": ["T030"] * 11,
                "graveyard": ["T002", "T004"]})
    drv = _Driver(play=_play_once("play:dm23ex3-tf03"))
    drv.run(e, lambda ev: "dm23ex3-tf03" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 8 and _quiet(ev))
    assert not _defns(e, "graveyard", 0)
    deck = _defns(e, "deck", 0)
    assert "T002" in deck and "T004" in deck
    assert len(e.zlist("shield", 0)) == 8


def test_registered_tf03_replacement():
    """味方が破壊される時、シールド2枚を手札に戻して味方が残る。"""
    e = _setup({"bz": ["dm23ex3-tf03", "T002"]},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"), choose=_choose_targets("T002"))
    drv.run(e, lambda ev: "T002" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 3 and _quiet(ev))
    assert "T002" not in _defns(e, "graveyard", 0)
    assert drv.seen.count("choose_replacement") == 1


# ---------- 実挙動: dm24ex4-042（登録形） ----------

def test_registered_042_protects_ally():
    """味方が破壊される時、シールド1つを手札に加えて味方が残る。"""
    e = _setup({"bz": ["dm24ex4-042", "T002"]},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"), choose=_choose_targets("T002"))
    drv.run(e, lambda ev: "T002" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 4 and _quiet(ev))
    assert "T002" not in _defns(e, "graveyard", 0)
    assert drv.seen.count("choose_replacement") == 1


def test_registered_042_does_not_protect_self():
    """「自分の他のクリーチャー」: エルナドンナ自身は守られない。"""
    e = _setup({"bz": ["dm24ex4-042"]},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"))
    drv.run(e, lambda ev: "dm24ex4-042" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "choose_replacement" not in drv.seen


# ---------- 実挙動: dmx23-025（登録形） ----------

def test_registered_henza_replacement():
    """味方が破壊される時、シールド2枚を手札に戻して味方が残る。"""
    e = _setup({"bz": ["dmx23-025", "T002"]},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"), choose=_choose_targets("T002"))
    drv.run(e, lambda ev: "T002" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 3 and _quiet(ev))
    assert "T002" not in _defns(e, "graveyard", 0)
    assert drv.seen.count("choose_replacement") == 1


# ---------- 実挙動: dm26rp3-001（登録形） ----------

def test_registered_rp3_cip_shield_mode():
    """出た時モード1: 山札の上から1枚がシールド化される。"""
    e = _setup({"hand": ["dm26rp3-001"], "mana": ["T030"] * 4})
    drv = _Driver(play=_play_once("play:dm26rp3-001"), modes=[0])
    drv.run(e, lambda ev: "dm26rp3-001" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 6 and _quiet(ev))
    assert len(e.zlist("shield", 0)) == 6


def test_registered_rp3_cip_jbig_mode():
    """出た時モード2（Jビッグ1）: 他のジョーカーズ（dm26rp3-077）の
    出た時の能力を使い、そのモード1でカードを1枚引く。"""
    e = _setup({"hand": ["dm26rp3-001"], "mana": ["T030"] * 4,
                "bz": ["dm26rp3-077"]})
    drv = _Driver(play=_play_once("play:dm26rp3-001"),
                  choose=_choose_targets("dm26rp3-077"), modes=[1, 0])
    drv.run(e, lambda ev: "dm26rp3-001" in _defns(ev, "bz", 0)
            and len(ev.zlist("hand", 0)) == 1 and _quiet(ev))
    assert _defns(e, "hand", 0) == ["T001"]


def test_registered_rp3_protects_jokers_only():
    """自分のジョーカーズが離れる時は守れるが、ジョーカーズでない
    味方は守れない（subject の race_has フィルタ）。"""
    e = _setup({"bz": ["dm26rp3-001", "dm26rp3-077"]},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"),
                  choose=_choose_targets("dm26rp3-077"))
    drv.run(e, lambda ev: "dm26rp3-077" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 4 and _quiet(ev))
    assert drv.seen.count("choose_replacement") == 1

    e = _setup({"bz": ["dm26rp3-001", "T002"]},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"), choose=_choose_targets("T002"))
    drv.run(e, lambda ev: "T002" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "choose_replacement" not in drv.seen


def test_registered_rp3_once_per_turn():
    """各ターンに1度: 同じターンに2体目のジョーカーズが離れる時は
    諮問されない。"""
    e = _setup({"bz": ["dm26rp3-001", "dm26rp3-077", "dm26rp3-013"]},
               {"hand": ["T056", "T056"], "mana": ["T056"] * 6})
    drv = _Driver(play=_play_times("play:T056", 2),
                  choose=_choose_targets("dm26rp3-077", "dm26rp3-013"))
    drv.run(e, lambda ev: len(_defns(ev, "graveyard", 0)) == 1 and _quiet(ev))
    assert len(_defns(e, "bz", 0)) == 2
    assert _defns(e, "graveyard", 0) == ["dm26rp3-013"]
    assert len(e.zlist("shield", 0)) == 4
    assert drv.seen.count("choose_replacement") == 1
