"""語彙パイロット第272弾: infinite_power / infinite_breaker（無限のパワー／ブレイク）。

対象は infinite_power ギャップ5件・infinite_breaker ギャップ5件（重なり1件）の
9枚。無限大は 1<<30 の整数で表す（G・ブレイカーの break count 1<<30 と同型）。

新語彙:
- キーワード `infinite_breaker`（∞ブレイカー）: 相手のシールドを好きな数
  ブレイクする。combat の攻撃フェイズ4でブレイク数の選択肢を 0..残シールド数
  にする（g_breaker の "all" とは別物: G・ブレイカーは全ブレイク＋自壊）。
- キーワード `infinite_power_attacker`（∞パワーアタッカー）: 攻撃中パワーが
  無限大になる。mod power_when {amount: 1<<30, when: attacking} で表す
  （パワーアタッカー+N の power_when と同型）。
- mod `power_set`: 「パワーを－∞にする」などのパワー置換。加算のすべてを
  上書きする（chars 計算の最後に最小の置換値を適用）。パワー0以下で状況起因
  処理（703.4c）が破壊する。
- 「バトル中、パワーを∞にする」（dm26rp2-s011 の条項）は新語彙なしで
  mod battle_power {amount: 1<<30}（only 無し＝攻守両方）で表せる。

Rust は infinite_breaker / infinite_power_attacker を _OK_KW に持たず、
power_set の modify も _simple_effect が弾くため、この能力を持つカードを
含む対局は Python にフォールバックする（ガチャ・trigger と同型）。
新しい GameState フィールドは無い（state.rs の変更なし）。
"""
import pytest
from tests.conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card
from dmsim.engine.rustcore import _OK_KW, _simple_effect

TABLES = load_tables()
INF = 1073741824


def _defns(e, zone, p):
    # zlist("bz", p) は共有ゾーンで両軍分を含むため、バトルゾーンは bz_tops で絞る
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _by_defn(e, zone, p):
    if zone == "bz":
        return {e.cdef(c).id: c for c in e.bz_tops(p)}
    return {e.cdef(c).id: c for c in e.zlist(zone, p)}


def _quiet(e):
    """誘発・効果の解決が終わった状態（効果・ジャンケン・待機誘発なし）。"""
    return (not any(t.get("t") in ("effect", "janken", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """汎用ドライバ（第271弾のものを流用＋ブレイク数・攻撃先の台本）。"""

    def __init__(self, play=None, choose=None, yes_no="yes", attack=None,
                 charge=None, breaker=None):
        self.play = play
        self.choose = choose
        self.yes_no = yes_no
        self.attack = attack
        self.charge = charge
        self.breaker = breaker
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


def _breaks(n):
    """choose_breaker で breaks:<n> を選ぶ。"""

    def breaker(e, d):
        keys = [o["key"] for o in d["options"]]
        return [keys.index(f"breaks:{n}")]

    return breaker


# ---------- parse / validation ----------

def test_pilot272_protos_parse():
    rules = load_rules()
    t758 = rules.cards["T758"]
    assert "infinite_breaker" in t758.keywords
    t759 = rules.cards["T759"]
    assert "infinite_power_attacker" in t759.keywords
    assert {"power_when": {"amount": INF, "when": "attacking"}} in [
        ab.get("mod") for ab in t759.abilities]
    t760 = rules.cards["T760"]
    assert [ab for ab in t760.abilities if ab["kind"] == "trigger"][0]["effect"][0]["mod"] == {"power_set": -INF}
    t761 = rules.cards["T761"]
    assert t761.spell[0]["mod"]["grant"] == ["infinite_power_attacker", "infinite_breaker"]
    assert t761.spell[0]["mod"]["gain"][0]["when"] == {"event": "battle_win", "subject": "self"}
    t762 = rules.cards["T762"]
    assert t762.abilities[0]["mod"] == {"battle_power": {"amount": INF}}
    # power_set は整数でなければならない
    with pytest.raises(DefError):
        parse_card({"id": "TX", "name": "x", "types": ["creature"], "civs": ["nature"],
                    "cost": 1, "power": 1000,
                    "abilities": [{"kind": "trigger",
                                   "when": {"event": "move", "to": "bz", "subject": "self"},
                                   "effect": [{"op": "modify",
                                              "select": {"ref": "self"},
                                              "mod": {"power_set": "inf"}}]}]},
                   TABLES)


def test_pilot272_not_rust_simple():
    # Rust は無限キーワードを知らず、power_set の modify も単純形ではない
    assert "infinite_breaker" not in _OK_KW
    assert "infinite_power_attacker" not in _OK_KW
    assert not _simple_effect([{"op": "modify",
                                "select": {"zone": ["bz"], "owner": "opp",
                                           "filter": {"types": ["creature"]}, "count": 1},
                                "mod": {"power_set": -INF}}])


# ---------- 実挙動: T758（∞ブレイカー） ----------

def test_infinite_breaker_choose_three(rules):
    """∞ブレイカー: 5枚のシールドから3枚だけブレイクできる。"""
    e = setup(rules, {"bz": ["T758"]},
              {"shield": ["T001", "T001", "T001", "T001", "T001"]})
    h0 = len(e.zlist("hand", 1))
    drv = _Driver(attack=_attack_once("attack:T758:player"), breaker=_breaks(3))
    # ブレイク解決とターン2のドローは同じ advance で観測されるため、手札は
    # ブレイク3枚＋ドロー1枚で h0+4 になる
    drv.run(e, lambda ev: len(e.zlist("shield", 1)) == 2 and _quiet(ev)
            and len(e.zlist("hand", 1)) == h0 + 4)
    assert len(e.zlist("shield", 1)) == 2
    assert len(e.zlist("hand", 1)) == h0 + 4
    assert "choose_breaker" in drv.seen_kinds


def test_infinite_breaker_choose_all(rules):
    """∞ブレイカー: 全ブレイクも選べる（ワールド・ブレイカーと違い強制ではない）。"""
    e = setup(rules, {"bz": ["T758"]},
              {"shield": ["T001", "T001"]})
    drv = _Driver(attack=_attack_once("attack:T758:player"), breaker=_breaks(2))
    drv.run(e, lambda ev: len(e.zlist("shield", 1)) == 0 and _quiet(ev))
    assert len(e.zlist("shield", 1)) == 0


# ---------- 実挙動: T759（∞パワーアタッカー） ----------

def test_infinite_power_attacker_wins(rules):
    """∞パワーアタッカー: パワー99999のブロッカーとのバトルに勝つ。"""
    e = setup(rules, {"bz": ["T759"]}, {"bz": ["T763"]})
    e.s.cards[_by_defn(e, "bz", 1)["T763"]].tapped = True
    drv = _Driver(attack=_attack_once("attack:T759:T763"))
    drv.run(e, lambda ev: "T763" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T763" in _defns(e, "graveyard", 1)
    assert "T759" in _defns(e, "bz", 0)


# ---------- 実挙動: T760（パワーを－∞にする） ----------

def test_power_set_neg_inf_destroys(rules):
    """出た時: 相手クリーチャーのパワーを－∞にし、状況起因処理で破壊する。"""
    e = setup(rules, {"hand": ["T760"], "mana": ["T760"] * 8},
              {"bz": ["T001"]})
    drv = _Driver(play=_play_once("play:T760"), choose=_first)
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T001" in _defns(e, "graveyard", 1)
    assert "T760" in _defns(e, "bz", 0)


# ---------- 実挙動: T761（付与呪文） ----------

def test_granted_infinite_keywords_battle_win_untap(rules):
    """付与: ∞パワーアタッカー＋∞ブレイカー＋バトル勝利時アンタップを得る。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T761"], "mana": ["T758"] * 13},
              {"bz": ["T763"]})
    e.s.cards[_by_defn(e, "bz", 1)["T763"]].tapped = True
    drv = _Driver(play=_play_once("play:T761"), choose=_first,
                  attack=_attack_once("attack:T001:T763"))
    t001 = _by_defn(e, "bz", 0)["T001"]

    def stop(ev):
        return ("T763" in _defns(ev, "graveyard", 1) and _quiet(ev)
                and not ev.s.cards[t001].tapped)

    drv.run(e, stop)
    assert "T763" in _defns(e, "graveyard", 1)
    assert "T001" in _defns(e, "bz", 0)
    assert not e.s.cards[t001].tapped   # バトル勝利時アンタップが働いた


def test_granted_infinite_breaker(rules):
    """付与された∞ブレイカーでも好きな数だけブレイクできる。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T761"], "mana": ["T758"] * 13},
              {"shield": ["T001", "T001", "T001", "T001"]})
    h0 = len(e.zlist("hand", 1))
    drv = _Driver(play=_play_once("play:T761"), choose=_first,
                  attack=_attack_once("attack:T001:player"), breaker=_breaks(2))
    # ブレイク解決とターン2のドローは同じ advance で観測されるため、手札は
    # ブレイク2枚＋ドロー1枚で h0+3 になる
    drv.run(e, lambda ev: len(e.zlist("shield", 1)) == 2 and _quiet(ev)
            and len(e.zlist("hand", 1)) == h0 + 3)
    assert len(e.zlist("shield", 1)) == 2
    assert len(e.zlist("hand", 1)) == h0 + 3


# ---------- 実挙動: T762（バトル中パワー∞） ----------

def test_battle_power_inf_as_blocker(rules):
    """バトル中パワー∞: パワー99999の攻撃クリーチャーをブロックして勝つ。"""
    e = setup(rules, {"bz": ["T762"]}, {"bz": ["T763"]})
    t762 = _by_defn(e, "bz", 0)["T762"]

    def charge_p1(ev, d):
        if ev.s.turn == 2 and d["player"] == 1:
            ev.s.cards[t762].tapped = True
        return None

    drv = _Driver(charge=charge_p1)

    def attack_p1(e, d):
        keys = [o["key"] for o in d["options"]]
        hit = [i for i, k in enumerate(keys) if k == "attack:T763:T762"]
        return [hit[0]] if hit else None

    drv.attack = attack_p1
    drv.run(e, lambda ev: "T763" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T763" in _defns(e, "graveyard", 1)
    assert "T762" in _defns(e, "bz", 0)
