"""語彙パイロット第271弾のカード適用テスト（登録形）。

ラウンド306で janken_opponent_hand の9件を再変換。
- 新規登録7件: dm28-056、dm28-060、dm28-103、dm29-035、dmex08-041、
  dmex08-171、dmex08-172、dmx22b-106 のうち dm28-103・dm29-031 を除く7件
  （dm28-103 は dmex08-041 の aliases、dm29-031 は dmex08-172 の
  aliases に収まったため stale 除去2件。最新版を正とする同名規則による）。
- 差し戻し0件。converted 10,108 → 10,115 / rejects 2,227 → 2,218、
  重複0・漏れ0。janken_opponent_hand ギャップは残り0件でファミリー解消。

プロトテスト（test_vocab_pilot271.py）とは別プロセスで実行すること
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


def _quiet(e):
    return (not any(t.get("t") in ("effect", "janken", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """第271弾のドライバ（ジャンケンの手の台本つき）。"""

    def __init__(self, play=None, choose=None, yes_no="yes", attack=None, hands=None,
                 charge=None):
        self.play = play
        self.choose = choose
        self.yes_no = yes_no
        self.attack = attack
        self.charge = charge
        self.hands = {p: list(v) for p, v in (hands or {}).items()}
        self.seen_kinds = []
        self.janken_throws = []

    def run(self, e, stop, limit=800):
        for _ in range(limit):
            d = e.advance()
            assert d is not None, "game ended"
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
            self.seen_kinds.append(kind)
            if kind == "choose_one" and "rock" in keys:
                q = self.hands.get(d["player"]) or []
                hand = q.pop(0) if q else "rock"
                self.janken_throws.append((d["player"], hand))
                e.answer([keys.index(hand)])
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


def _first(e, d):
    return [0]


# ---------- 登録形 ----------

def test_round306_registered_forms():
    c = _converted("dm28-056")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["name"] == "JK人形ボッコグー"
    assert c["types"] == ["creature"] and c["civs"] == ["darkness"]
    assert c["cost"] == 3 and c["power"] == 2000
    assert c["races"] == ["デスパペット"]
    assert c["abilities"][0] == {
        "kind": "activate", "cost": {"tap": "self"},
        "effect": [{"op": "janken", "win": [
            {"op": "modify",
             "select": {"zone": "bz", "owner": "opp",
                        "filter": {"types": ["creature"]}, "count": 1},
             "mod": {"power": -3000}, "duration": "end_of_turn"}]}]}
    assert c["abilities"][1]["when"] == {"event": "janken", "opp_hand": "paper"}
    # バトルする時は攻撃側・守備側の2つの trigger に分かれる（dmr01-020 と同型）
    c60 = _converted("dm28-060")
    parse_card(copy.deepcopy(c60), TABLES)
    assert [a["when"] for a in c60["abilities"][:2]] == [
        {"event": "battle_start", "subject": "self"},
        {"event": "battle_start", "opponent": "self"}]
    assert c60["abilities"][2]["when"] == {"event": "janken", "opp_hand": "rock"}
    # 旧版は最新版の aliases に収まる（同名規則）
    assert "dm28-103" in _converted("dmex08-041")["source"]["aliases"]
    assert "dm29-031" in _converted("dmex08-172")["source"]["aliases"]
    assert _converted("dm29-035")["source"]["aliases"] == ["dm29-035hc"]
    assert _converted("dmx22b-106")["abilities"][0]["kind"] == "replace"
    assert _converted("dmx22b-106")["abilities"][0]["when"] == {
        "event": "battle_start", "subject": "self"}
    assert _converted("dmex08-171")["abilities"][1]["when"] == {
        "event": "janken", "opp_hand": "paper"}
    for cid in ("dm28-056", "dm28-060", "dm29-035",
                "dmex08-041", "dmex08-171", "dmex08-172", "dmx22b-106"):
        parse_card(copy.deepcopy(_converted(cid)), TABLES)


def test_round306_no_rejects_left():
    """janken_opponent_hand ギャップは残り0件。9件すべて解決済み。"""
    for cid in ("dm28-056", "dm28-060", "dm28-103", "dm29-031", "dm29-035",
                "dmex08-041", "dmex08-171", "dmex08-172", "dmx22b-106"):
        with pytest.raises(KeyError):
            _reject(cid)
    left = [json.loads(l)["id"] for l in open(REJECTS, encoding="utf-8")
            if "janken_opponent_hand" in (json.loads(l).get("gaps") or [])]
    assert left == []


# ---------- 実挙動（登録形） ----------

def test_registered_dmex08_172_entry_win_speed_attacker():
    """出た時ジャンケンに勝ち、そのターン speed_attacker を得る。
    dm29-031 は dmex08-172 の alias のため、正規 ID で置く。"""
    e = _setup(load_rules(), {"hand": ["dmex08-172"], "mana": ["T011", "T011"]},
               {"hand": ["T001", "T002"]})
    drv = _Driver(play=_play_once("play:dmex08-172"),
                  hands={0: ["rock"], 1: ["scissors"]})
    cid = None

    def stop(ev):
        nonlocal cid
        m = _by_defn(ev, "bz", 0).get("dmex08-172")
        if m is None:
            return False
        cid = m
        return ("speed_attacker" in ev.chars_ro(m)["keywords"] and _quiet(ev))

    drv.run(e, stop)
    assert "dmex08-172" in _defns(e, "bz", 0)
    assert "speed_attacker" in e.chars_ro(cid)["keywords"]
    recs = [r for r in e.s.pub if r.get("kind") == "janken"]
    assert len(recs) == 1 and recs[0]["winner"] == 0


def test_registered_dmex08_172_rock_destroys():
    """負けてグー誘発: 相手のパワー2000以下を破壊する。相手がグーを出す必要があるため
    こちらはチョキで負ける。"""
    e = _setup(load_rules(), {"hand": ["dmex08-172"], "mana": ["T011", "T011"]},
               {"bz": ["T001"], "hand": ["T001", "T002"]})
    drv = _Driver(play=_play_once("play:dmex08-172"), choose=_first,
                  hands={0: ["scissors"], 1: ["rock"]})
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T001" in _defns(e, "graveyard", 1)
    assert "dmex08-172" in _defns(e, "bz", 0)
    recs = [r for r in e.s.pub if r.get("kind") == "janken"]
    assert len(recs) == 1 and recs[0]["winner"] == 1


def test_registered_dmex08_171_win_moves_grave_creature():
    """勝ち: 墓地のコスト5以下をバトルゾーンに出す。"""
    e = _setup(load_rules(),
               {"hand": ["dmex08-171"], "mana": ["T008"] + ["T001"] * 4,
                "graveyard": ["T001"]},
               {"hand": ["T001", "T002"]})
    drv = _Driver(play=_play_once("play:dmex08-171"), choose=_first,
                  hands={0: ["rock"], 1: ["scissors"]})
    drv.run(e, lambda ev: "T001" in _defns(ev, "bz", 0) and _quiet(ev))
    assert "T001" in _defns(e, "bz", 0)
    assert "dmex08-171" in _defns(e, "bz", 0)


def test_registered_dmex08_041_attack_may_janken():
    """攻撃時 may ジャンケンに勝ち、相手クリーチャーをマナへ。チョキで山札の上をマナへ。"""
    e = _setup(load_rules(), {"bz": ["dmex08-041"], "mana": ["T005"]},
               {"bz": ["T001"]})
    m0 = len(e.zlist("mana", 0))
    drv = _Driver(attack=_attack_once("attack:dmex08-041:player"),
                  hands={0: ["rock"], 1: ["scissors"]})
    drv.run(e, lambda ev: "T001" in _defns(ev, "mana", 1) and _quiet(ev)
            and len(ev.zlist("mana", 0)) == m0 + 1)
    assert "T001" in _defns(e, "mana", 1)   # 勝ち: 相手クリーチャーを持ち主のマナへ
    assert len(e.zlist("mana", 0)) == m0 + 1  # チョキ誘発: 山札の上をマナへ


def test_registered_dmx22b_106_battle_replace():
    """バトル置換: 攻撃側が勝ち、負けた相手のバトル中クリーチャーが破壊される。"""
    e = _setup(load_rules(), {"bz": ["dmx22b-106"]}, {"bz": ["T001"]})
    e.s.cards[_by_defn(e, "bz", 1)["T001"]].tapped = True
    drv = _Driver(attack=_attack_once("attack:dmx22b-106:T001"),
                  hands={0: ["rock"], 1: ["scissors"]})
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T001" in _defns(e, "graveyard", 1)
    assert "dmx22b-106" in _defns(e, "bz", 0)
    recs = [r for r in e.s.pub if r.get("kind") == "janken"]
    assert len(recs) == 1 and recs[0]["turn"] == 1


def test_registered_dm28_060_battle_win_power():
    """バトルする時ジャンケンに勝ち、パワー+5000。バトルで相手だけが破壊される。
    （+5000が無ければ同パワーで相打ちになるため、攻撃側の生存がバフの証明。
    +5000の数値自体は登録形テストで検証。バトル直後にターンが終わるため
    パワー値そのものはこのテストでは観測しない）"""
    e = _setup(load_rules(), {"bz": ["dm28-060"]},
               {"bz": ["T001"], "mana": ["T002"]})
    e.s.cards[_by_defn(e, "bz", 1)["T001"]].tapped = True
    drv = _Driver(attack=_attack_once("attack:dm28-060:T001"),
                  hands={0: ["rock"], 1: ["scissors"]})
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 1)
            and "dm28-060" in _defns(ev, "bz", 0) and _quiet(ev))
    assert "T001" in _defns(e, "graveyard", 1)   # バトルで破壊された
    assert "dm28-060" in _defns(e, "bz", 0)   # +5000で勝ち、生き残った
    assert len(e.zlist("mana", 1)) == 1   # チョキではグー誘発なし
    recs = [r for r in e.s.pub if r.get("kind") == "janken"]
    assert len(recs) == 1 and recs[0]["winner"] == 0


def test_registered_dm28_060_rock_mana_to_grave():
    """グー誘発: 相手は自分のマナゾーンからカードを1枚選び、墓地に置く。
    相手がグーを出す必要があるためこちらはチョキで負ける（バトルは同パワーで相打ち）。"""
    e = _setup(load_rules(), {"bz": ["dm28-060"]},
               {"bz": ["T001"], "mana": ["T002"]})
    e.s.cards[_by_defn(e, "bz", 1)["T001"]].tapped = True
    drv = _Driver(attack=_attack_once("attack:dm28-060:T001"), choose=_first,
                  hands={0: ["scissors"], 1: ["rock"]})
    drv.run(e, lambda ev: "T002" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T002" in _defns(e, "graveyard", 1)   # グー誘発: マナから墓地へ
    assert "T001" in _defns(e, "graveyard", 1)   # バトルで相打ち


def test_registered_dm28_056_activate_win():
    """起動型: タップしてジャンケンに勝ち、相手クリーチャーのパワーを-3000。
    パワー2000の対象は0以下になって破壊される（-3000の数値は登録形テストで検証）。
    起動型の効果解決後にターンが終わるため、パワー値そのものはこのテストでは観測しない。"""
    e = _setup(load_rules(), {"bz": ["dm28-056"]},
               {"bz": ["T001"], "hand": ["T001", "T002"]})
    drv = _Driver(attack=_attack_once("activate:dm28-056:0"), choose=_first,
                  hands={0: ["rock"], 1: ["scissors"]})
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T001" in _defns(e, "graveyard", 1)   # パワー-3000で0以下になり破壊された
    assert "dm28-056" in _defns(e, "bz", 0)
    recs = [r for r in e.s.pub if r.get("kind") == "janken"]
    assert len(recs) == 1 and recs[0]["winner"] == 0


def test_registered_dm28_056_paper_discard():
    """負けてパー誘発: 相手は自分の手札を1枚捨てる。"""
    e = _setup(load_rules(), {"bz": ["dm28-056"]},
               {"bz": ["dmex08-041"], "hand": ["T001", "T002"]})
    h1 = len(e.zlist("hand", 1))
    drv = _Driver(attack=_attack_once("activate:dm28-056:0"), choose=_first,
                  hands={0: ["rock"], 1: ["paper"]})
    drv.run(e, lambda ev: len(ev.zlist("graveyard", 1)) >= 1 and _quiet(ev))
    assert len(e.zlist("hand", 1)) == h1   # -1（捨てた）+1（ターン2のドロー）
    assert len(e.zlist("graveyard", 1)) >= 1


def test_registered_dm29_035_cross_gear():
    """ギアを生成してクロスし、宿主で攻撃。勝ってマナからサムライを出し、チョキで山札の上をマナへ。"""
    e = _setup(load_rules(),
               {"hand": ["dm29-035"],
                "mana": ["T001", "T001", "T001", "T001", "T001", "dm31-040"],
                "bz": ["T005"]},
               {"bz": []})
    m0 = len(e.zlist("mana", 0))

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        for want in ("play:dm29-035", "cross:dm29-035:T005"):
            if want in keys:
                return [keys.index(want)]
        return None

    drv = _Driver(play=play, attack=_attack_once("attack:T005:player"),
                  hands={0: ["rock"], 1: ["scissors"]})

    def stop(ev):
        g = _by_defn(ev, "bz", 0).get("dm29-035")
        return (g is not None and ev.s.cards[g].crossed is not None
                and "dm31-040" in _defns(ev, "bz", 0)
                and len(ev.zlist("mana", 0)) == m0 and _quiet(ev))

    drv.run(e, stop)
    g = _by_defn(e, "bz", 0)["dm29-035"]
    host = _by_defn(e, "bz", 0)["T005"]
    assert list(e.s.cards[g].crossed) == list(e.s.ref(host))
    assert "dm31-040" in _defns(e, "bz", 0)   # 勝ち: マナからサムライを出した
    assert len(e.zlist("mana", 0)) == m0      # -1（出した）+1（チョキ誘発）
