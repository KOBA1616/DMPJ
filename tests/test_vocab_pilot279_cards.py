"""語彙パイロット第279弾のカード適用テスト（登録形）。

ラウンド314で alt_cost_mana_civilization_condition の純粋4件をすべて
新規登録、差し戻しなし。
- dm25ex3-054 ～破壊と殺戮の連鎖～（光・水・闇、alias: dm25rp4-049）
- dm25ex3-057 大集合！アカネ&アサギ&コハク（光・水・自然、
  alias: dm25rp4-050 / promoy25-120）
- dm25ex3-062 哀蛇の虚 シンロッチ（闇・火・自然、alias: dm25rp4-053）
- dm25ex3-060 トレース＝トレーシー（水・闇・火、alias: dm25rp4-052）
4件とも partial の alt_cost を本弾の形 {cost: 2, civs: [], if: {all:
[exists {zone: mana, owner: you, filter: {civs: [文明]}} ×3]}} に
差し替えて提出した。partial の civs: [zero, zero] は誤記（[cc02] の
正表現は civs: []）。

dm25ex3-062 の攻撃時誘発は原文「自分の山札の上から2枚を表向きにする」
のため、partial の choose（look: true のみ）を reveal: true に直した
（look を外し op に reveal を付ける。dm23rp1-071 の登録先例形。
「見る」だけの dm25ex3-057 は look: true のまま）。
submit は partial の abilities と回答を連結する（第313弾の教訓）ため、
登録形の abilities が回答と完全一致することも検証済み（本ファイルの
test_registered_forms が abilities の完全一致を固定する）。
converted 10,145 / rejects 2,188、重複0・漏れ0。
alt_cost_mana_civilization_condition は残り0件でファミリー解消。

プロトテスト（test_vocab_pilot279.py）とは別プロセスで実行すること
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
from dmsim.engine.scenario import build  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
IDS = ["dm25ex3-054", "dm25ex3-057", "dm25ex3-062", "dm25ex3-060"]

ALIASES = {
    "dm25ex3-054": ["dm25rp4-049"],
    "dm25ex3-057": ["dm25rp4-050", "promoy25-120"],
    "dm25ex3-062": ["dm25rp4-053"],
    "dm25ex3-060": ["dm25rp4-052"],
}

TEXTS = {
    "dm25ex3-054":
        "自分のマナゾーンに光、水、闇の各文明があれば、このクリーチャーを[cc02]支払って召喚してもよい。\n"
        "NEO進化：光、水、または闇のクリーチャー１体の上に置いてもよい。（カードが下にあれば、これをNEO進化クリーチャーとして扱う）\n"
        "このクリーチャーが出た時、自分の山札の上から１枚をシールド化する。",
    "dm25ex3-057":
        "自分のマナゾーンに光、水、自然の各文明があれば、このクリーチャーを[cc02]支払って召喚してもよい。\n"
        "NEO進化：光、水、または自然のクリーチャー１体の上に置いてもよい。（カードが下にあれば、これをNEO進化クリーチャーとして扱う）\n"
        "このクリーチャーが出た時、自分の山札の上から２枚を見る。その中から１枚を手札に加えるかマナゾーンに置き、残りの１枚を山札の下に置く。",
    "dm25ex3-062":
        "自分のマナゾーンに闇、火、自然の各文明があれば、このクリーチャーを[cc02]支払って召喚してもよい。\n"
        "NEO進化：闇、火、または自然のクリーチャー１体の上に置いてもよい。（カードが下にあれば、これをNEO進化クリーチャーとして扱う）\n"
        "このクリーチャーが攻撃する時、自分の山札の上から２枚を表向きにする。その中からクリーチャーを１体手札に加えてもよい。残りを墓地に置く。",
    "dm25ex3-060":
        "自分のマナゾーンに水、闇、火の各文明があれば、このクリーチャーを[cc02]支払って召喚してもよい。\n"
        "NEO進化：水、闇、または火のクリーチャー１体の上に置いてもよい。（カードが下にあれば、これをNEO進化クリーチャーとして扱う）\n"
        "このクリーチャーが出た時、自分の山札の上から１枚を墓地に置く。その後、クリーチャーまたはタマシードを１つ、自分の墓地から手札に戻してもよい。",
}

CIP = {"event": "move", "subject": "self", "to": "bz"}

ABILITIES = {
    "dm25ex3-054": [
        {"kind": "trigger", "when": CIP,
         "effect": [{"op": "move", "reason": "put",
                     "select": {"from_top": 1, "owner": "you", "zone": "deck"},
                     "to": "shield"}]}],
    "dm25ex3-057": [
        {"kind": "trigger", "when": CIP,
         "effect": [
             {"op": "choose", "as": "pile",
              "select": {"count": "all", "from_top": 2, "look": True,
                         "owner": "you", "zone": "deck"}},
             {"op": "choose", "as": "c",
              "select": {"count": 1, "ref": "pile"}},
             {"op": "modal",
              "modes": [[{"op": "move", "reason": "put",
                          "select": {"count": "all", "ref": "c"},
                          "to": "hand"}],
                        [{"op": "mana_put",
                          "select": {"count": "all", "ref": "c"}}]]},
             {"op": "move", "position": "bottom", "reason": "put",
              "select": {"count": "all", "ref": "pile"}, "to": "deck"}]}],
    "dm25ex3-062": [
        {"kind": "trigger", "when": {"event": "attack", "subject": "self"},
         "effect": [
             {"op": "choose", "as": "pile", "reveal": True,
              "select": {"count": "all", "from_top": 2,
                         "owner": "you", "zone": "deck"}},
             {"op": "choose", "as": "hit",
              "select": {"count": 1, "filter": {"types": ["creature"]},
                         "ref": "pile"}},
             {"op": "may",
              "body": [{"op": "move", "reason": "put",
                        "select": {"count": "all", "ref": "hit"},
                        "to": "hand"}]},
             {"op": "move", "reason": "put",
              "select": {"count": "all", "ref": "pile"},
              "to": "graveyard"}]}],
    "dm25ex3-060": [
        {"kind": "trigger", "when": CIP,
         "effect": [
             {"op": "mill", "count": 1, "owner": "you"},
             {"op": "may",
              "body": [{"op": "move", "reason": "return",
                        "select": {"count": 1,
                                   "filter": {"types": ["creature", "tamaseed"]},
                                   "owner": "you", "zone": "graveyard"},
                        "to": "hand"}]}]}],
}


def _alt_cost(civs):
    return {"cost": 2, "civs": [],
            "if": {"all": [{"exists": {"zone": "mana", "owner": "you",
                                       "filter": {"civs": [c]}}}
                            for c in civs]}}


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


def _tapped_mana(e, p=0):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


class _Driver:
    """汎用ドライバ（第278弾 cards と同形＋ choose_mode は先頭モード、
    play フックは attack 決定にも掛ける。攻撃宣言は main と別の
    attack 決定で提示されるため）。

    play: main / attack 決定で (e, d) -> 答えのリストか None を返すフック。
    choose: choose_cards へのフック (e, d) -> 答えのリストか None。
    """

    def __init__(self, play=None, choose=None):
        self.play = play
        self.choose = choose
        self.seen = []

    def run(self, e, stop, limit=1200):
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
            if kind in ("main", "attack") and self.play is not None:
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
            elif kind == "choose_mode":
                e.answer([0])
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


def _main_keys(e):
    """charge を pass して最初の main 決定の選択肢キーを返す（第279弾と同形）。"""
    d = e.advance()
    for _ in range(12):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main":
            return keys
        e.answer([keys.index("pass")] if "pass" in keys else [0])
        d = e.advance()
    raise AssertionError("main not reached")


# ---------- 登録形 ----------

def test_registered_forms():
    for cid in IDS:
        c = _converted(cid)
        d = parse_card(copy.deepcopy(c), TABLES)
        assert "unsupported" not in (c.get("source") or {}), cid
        try:
            _reject(cid)
            raise AssertionError(f"{cid} が rejects に残っている")
        except KeyError:
            pass
        assert c["source"]["aliases"] == ALIASES[cid], cid
        assert c["types"] == ["creature"] and c["cost"] == 3, cid
        assert c["power"] == 3000 and c.get("keywords") in (None, []), cid
        assert c["text"] == TEXTS[cid], cid
        # alt_cost は本弾の形（civs: [] ＋ 自カードの3文明ぶんの exists）
        assert c["alt_cost"] == _alt_cost(c["civs"]), cid
        assert d.alt_cost == _alt_cost(c["civs"]), cid
        assert d.neo and d.evolve_from == {"civs": c["civs"]}, cid
        # abilities は回答と完全一致（partial 残存なし。第313弾の教訓）
        assert c["abilities"] == ABILITIES[cid], cid

    assert _converted("dm25ex3-054")["name"] == "～破壊と殺戮の連鎖～"
    assert _converted("dm25ex3-054")["civs"] == ["light", "water", "darkness"]
    assert _converted("dm25ex3-054")["races"] == [
        "デーモン・コマンド", "パラサイトワーム", "スチーム・ナイト"]
    assert _converted("dm25ex3-057")["name"] == "大集合！アカネ&アサギ&コハク"
    assert _converted("dm25ex3-057")["civs"] == ["light", "water", "nature"]
    assert _converted("dm25ex3-062")["name"] == "哀蛇の虚 シンロッチ"
    assert _converted("dm25ex3-062")["civs"] == ["darkness", "fire", "nature"]
    assert _converted("dm25ex3-060")["name"] == "トレース＝トレーシー"
    assert _converted("dm25ex3-060")["civs"] == ["water", "darkness", "fire"]


# ---------- 実挙動: dm25ex3-054 の代替コスト ----------

def test_registered_054_alt_offered():
    """マナに光・水・闇があれば :alt が出る（通常召喚も可）。"""
    e = _setup(load_rules(), {"hand": ["dm25ex3-054"],
                              "mana": ["T004", "T010", "T008"]},
               {"bz": ["T001"]})
    keys = _main_keys(e)
    assert "play:dm25ex3-054:alt" in keys
    assert "play:dm25ex3-054" in keys


def test_registered_054_alt_not_offered_without_darkness():
    """闇が無ければ :alt は出ない（通常召喚も闇不足で不可）。"""
    e = _setup(load_rules(), {"hand": ["dm25ex3-054"],
                              "mana": ["T004", "T010", "T001", "T001"]},
               {"bz": ["T001"]})
    keys = _main_keys(e)
    assert "play:T001" in keys          # main が提示されていることの確認
    assert "play:dm25ex3-054:alt" not in keys
    assert "play:dm25ex3-054" not in keys


def test_registered_054_alt_payment_and_cip_shield():
    """:alt は2枚タップで召喚でき、出た時に山札の上から1枚をシールド化する。"""
    e = _setup(load_rules(), {"hand": ["dm25ex3-054"],
                              "mana": ["T004", "T010", "T008"]},
               {"bz": ["T001"]})
    assert len(e.zlist("shield", 0)) == 5
    drv = _Driver(play=_play_once("play:dm25ex3-054:alt"))
    drv.run(e, lambda ev: "dm25ex3-054" in _defns(ev, "bz", 0) and _quiet(ev))
    assert _tapped_mana(e) == 2
    assert len(e.zlist("shield", 0)) == 6   # CIP で上から1枚がシールド化


# ---------- 実挙動: dm25ex3-057 の出た時 ----------

def test_registered_057_cip_look_choose_bottom():
    """出た時: 上から2枚を見て1枚を手札へ（モード0）、残りを山札の下へ。"""
    e = _setup(load_rules(), {"hand": ["dm25ex3-057"],
                              "mana": ["T004", "T010", "T007"]},
               {"bz": ["T001"]})
    snap = {}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if "play:dm25ex3-057" in keys and "top2" not in snap:
            snap["top2"] = list(e.zlist("deck", 0)[:2])
            return [keys.index("play:dm25ex3-057")]
        return None

    def choose(e, d):
        if "picked" not in snap and len(d["options"]) == 2:
            snap["picked"] = d["options"][0]["cid"]
            return [0]
        return None

    drv = _Driver(play=play, choose=choose)
    drv.run(e, lambda ev: "dm25ex3-057" in _defns(ev, "bz", 0) and _quiet(ev)
            and "picked" in snap)
    picked = snap["picked"]
    rest = [c for c in snap["top2"] if c != picked]
    assert len(rest) == 1
    assert picked in e.zlist("hand", 0)               # 選んだ1枚は手札へ
    assert e.zlist("deck", 0)[-1] == rest[0]          # 残りは山札の一番下


# ---------- 実挙動: dm25ex3-062 の攻撃時（表向き） ----------

def test_registered_062_attack_reveals_top2():
    """攻撃する時: 上から2枚を表向きにし（reveal の公開記録が両プレイヤー
    向けに残る）、クリーチャー1体を手札へ、残りを墓地へ。"""
    e = _setup(load_rules(), {"bz": ["dm25ex3-062"], "mana": ["T001"]},
               {"bz": ["T001"]})
    snap = {}

    def play(e, d):
        for i, o in enumerate(d["options"]):
            if o["key"].startswith("attack:dm25ex3-062") and "top2" not in snap:
                snap["top2"] = list(e.zlist("deck", 0)[:2])
                return [i]
        return None

    def choose(e, d):
        if "picked" not in snap and d["options"]:
            snap["picked"] = d["options"][0]["cid"]
            return [0]
        return None

    drv = _Driver(play=play, choose=choose)
    drv.run(e, lambda ev: "picked" in snap
            and snap.get("picked") in ev.zlist("hand", 0) and _quiet(ev))
    picked = snap["picked"]
    rest = [c for c in snap["top2"] if c != picked]
    assert len(rest) == 1
    assert rest[0] in e.zlist("graveyard", 0)         # 残りは墓地へ
    revealed = {r["cid"] for r in e.s.pub
                if r["kind"] == "reveal" and r["viewers"] == [0, 1]}
    assert set(snap["top2"]) <= revealed             # 2枚とも表向き（公開）


# ---------- 実挙動: dm25ex3-060 の出た時 ----------

def test_registered_060_cip_mill_and_return():
    """出た時: 上から1枚を墓地に置き、その後、墓地のクリーチャーを
    1つ手札に戻してもよい。"""
    e = _setup(load_rules(), {"hand": ["dm25ex3-060"],
                              "mana": ["T010", "T008", "T034"],
                              "graveyard": ["T004"]},
               {"bz": ["T001"]})
    snap = {}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if "play:dm25ex3-060" in keys and "top1" not in snap:
            snap["top1"] = e.zlist("deck", 0)[0]
            return [keys.index("play:dm25ex3-060")]
        return None

    def choose(e, d):
        defns = [e.cdef(o["cid"]).id for o in d["options"]]
        if "T004" in defns:
            snap["returned"] = d["options"][defns.index("T004")]["cid"]
            return [defns.index("T004")]
        return None

    drv = _Driver(play=play, choose=choose)
    drv.run(e, lambda ev: "dm25ex3-060" in _defns(ev, "bz", 0) and _quiet(ev)
            and "returned" in snap)
    assert snap["top1"] in e.zlist("graveyard", 0)    # 上から1枚が墓地へ
    assert snap["returned"] in e.zlist("hand", 0)     # 墓地の T004 が手札へ
    assert "T004" not in _defns(e, "graveyard", 0)
