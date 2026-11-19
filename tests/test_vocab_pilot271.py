"""語彙パイロット第271弾: janken_opponent_hand（相手の出した手への誘発）。

「相手とジャンケンで勝敗を決める」＋「相手がジャンケンで「X」を出した時」の2文型。
DM のジャンケンは「勝敗が決まるまでやって一回」で、あいこは勝敗が決まるまで
やり直す（デュエル・マスターズ Wiki「ジャンケン」）。あいこの投で相手がその手を
出しても誘発し、勝敗が決まってから溜まった分をまとめて解決する。
そのため手の条項は分岐ではなく、ジャンケン1投ごとに発表される janken イベントを
見る誘発型能力（when: {event: janken, opp_hand: rock|scissors|paper}）で表す。
勝った側の効果が先に解決され、その後で溜まった手の誘発が解決される（603.3）。

新語彙:
- op `janken` の専用タスク化（第31弾の op 内二段 ask は不発だった: 1人目の
  答えが返った時点で h_effect が pc を進めて os を消し、相手の手を尋ねる前に
  終わって分岐が一度も走らない。第31弾のテストはターンのドローと区別できず
  見逃していた。既存の4枚のジャンケン能力はこの修正で初めて動くようになる）。
- イベント `janken`（1投ごと。hands: プレイヤー順の手、winner: 勝者・あいこは None）。
  各投は s.pub に kind: "janken" で公開記録する（ガチャと同型）。
- when の `opp_hand`（相手＝この能力のコントローラーの対戦相手が出した手）。
- `draw` 分岐の削除: あいこに「あいこという判定」は無いので draw 分岐は死に語彙。
  既存の4枚は draw を使っていない。

Rust は event "janken"・when の opp_hand・op janken を知らないため、この能力を
持つカードを含む対局は Python にフォールバックする（ガチャ・trigger と同型）。
新しい GameState フィールドは無い（state.rs の変更なし）。
"""
import pytest
from tests.conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card
from dmsim.engine.rustcore import _simple_when

TABLES = load_tables()


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
    """ジャンケンとその誘発の解決が終わった状態（効果・ジャンケン・待機誘発なし）。"""
    return (not any(t.get("t") in ("effect", "janken", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """汎用ドライバ（第270弾のものを流用＋ジャンケンの手の台本）。

    hands: {player: [手, ...]} — choose_one が来るたびにそのプレイヤーの
    台本から1つずつ出す。台本が尽きたら rock を出す。
    """

    def __init__(self, play=None, choose=None, yes_no="yes", attack=None, hands=None,
                 charge=None):
        self.play = play
        self.choose = choose
        self.yes_no = yes_no
        self.attack = attack
        self.charge = charge
        self.hands = {p: list(v) for p, v in (hands or {}).items()}
        self.seen_kinds = []
        self.janken_throws = []   # (player, hand) — 尋ねられた順

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


# ---------- parse / validation ----------

def test_pilot271_protos_parse():
    rules = load_rules()
    t753 = rules.cards["T753"]
    assert t753.abilities[0]["effect"] == [{"op": "janken", "win": [{"op": "draw", "count": 1}]}]
    assert t753.abilities[1]["when"] == {"event": "janken", "opp_hand": "paper"}
    assert rules.cards["T754"].abilities[1]["when"] == {"event": "janken", "opp_hand": "scissors"}
    assert rules.cards["T755"].abilities[2]["when"] == {"event": "janken", "opp_hand": "rock"}
    assert rules.cards["T756"].abilities[0]["when"] == {"event": "janken", "opp_hand": "paper"}
    # draw 分岐は死に語彙: 書くと検証で弾かれる
    with pytest.raises(DefError):
        parse_card({"id": "TX", "name": "x", "types": ["creature"], "civs": ["nature"],
                    "cost": 1, "power": 1000,
                    "abilities": [{"kind": "trigger",
                                   "when": {"event": "move", "to": "bz", "subject": "self"},
                                   "effect": [{"op": "janken", "draw": [{"op": "draw", "count": 1}]}]}]},
                   TABLES)
    with pytest.raises(DefError):
        parse_card({"id": "TX", "name": "x", "types": ["creature"], "civs": ["nature"],
                    "cost": 1, "power": 1000,
                    "abilities": [{"kind": "trigger",
                                   "when": {"event": "janken", "opp_hand": "lizard"},
                                   "effect": [{"op": "draw", "count": 1}]}]},
                   TABLES)


def test_pilot271_janken_event_not_rust_simple():
    # Rust は janken イベント・opp_hand を知らないので Python にフォールバックする
    assert not _simple_when({"event": "janken", "opp_hand": "paper"})
    assert not _simple_when({"event": "move", "to": "bz", "subject": "self",
                             "opp_hand": "paper"})


# ---------- 実挙動: T753（出た時ジャンケン＋パーで相手ハンデス） ----------

def test_janken_win_draws(rules):
    """勝ち: 自分グー・相手チョキで勝ち、1ドローする。ターン1のうちに決まる。"""
    e = setup(rules, {"hand": ["T753"], "mana": ["T001", "T001", "T001"]},
              {"hand": ["T001", "T002"]})
    h0 = len(e.zlist("hand", 0))
    drv = _Driver(play=_play_once("play:T753"), hands={0: ["rock"], 1: ["scissors"]})
    drv.run(e, lambda ev: "T753" in _defns(ev, "bz", 0) and _quiet(ev)
            and len(e.zlist("hand", 0)) == h0)
    # 停止は次のプレイヤーのチャージ（ターン2）で初めて観測される（メインは
    # pass しか残らず自動で進むため）。p0 が次に引くのはターン3なので、ターン2
    # 時点の手札はジャンケンのドローによるもの（ターンドローの混入なし）。
    assert e.s.turn <= 2
    assert len(e.zlist("hand", 0)) == h0   # -1（出した）+1ドロー
    assert len(e.zlist("hand", 1)) == 3    # 相手はチョキ: パー誘発なし（2枚＋ターン2のドロー1枚）
    recs = [r for r in e.s.pub if r.get("kind") == "janken"]
    assert len(recs) == 1
    assert recs[0]["hands"] == ["rock", "scissors"] and recs[0]["winner"] == 0


def test_janken_lose_and_opp_hand_discards(rules):
    """負け＋手の誘発: 自分グー・相手パーで負け、ドローなし。相手のパーで相手が1枚捨てる。"""
    e = setup(rules, {"hand": ["T753"], "mana": ["T001", "T001", "T001"]},
              {"hand": ["T001", "T002"]})
    h0 = len(e.zlist("hand", 0))
    drv = _Driver(play=_play_once("play:T753"), choose=_first,
                  hands={0: ["rock"], 1: ["paper"]})
    drv.run(e, lambda ev: "T753" in _defns(ev, "bz", 0) and _quiet(ev)
            and len(e.zlist("graveyard", 1)) >= 1)
    assert e.s.turn <= 2   # 同上（停止はターン2のチャージで初めて観測される）
    assert len(e.zlist("hand", 0)) == h0 - 1   # 負け: ドローなし
    assert len(e.zlist("hand", 1)) == 2        # パー誘発: 相手が1枚捨てた（2-1＋ターン2のドロー1枚）
    recs = [r for r in e.s.pub if r.get("kind") == "janken"]
    assert len(recs) == 1 and recs[0]["winner"] == 1


def test_janken_draw_redo_accumulates_hand_triggers(rules):
    """あいこはやり直し、あいこの投のパーも誘発する: 1投目パー/パーであいこ、
    2投目チョキ/パーで勝ち。勝ちの1ドローが先に解決され、その後でパー誘発2回分
    （相手が2枚捨てる）が解決される。"""
    e = setup(rules, {"hand": ["T753"], "mana": ["T001", "T001", "T001"]},
              {"hand": ["T001", "T002"]})
    h0 = len(e.zlist("hand", 0))
    seen_discard_with_draw = {}

    def choose(e, d):
        # 相手の捨て札の選択が出た時点で、勝ちの1ドローは解決済みのはず
        seen_discard_with_draw["hand"] = len(e.zlist("hand", 0))
        return [0]

    drv = _Driver(play=_play_once("play:T753"), choose=choose,
                  hands={0: ["paper", "scissors"], 1: ["paper", "paper"]})
    drv.run(e, lambda ev: "T753" in _defns(ev, "bz", 0) and _quiet(ev)
            and len(e.zlist("graveyard", 1)) >= 2)
    assert drv.janken_throws == [(0, "paper"), (1, "paper"), (0, "scissors"), (1, "paper")]
    recs = [r for r in e.s.pub if r.get("kind") == "janken"]
    assert len(recs) == 2
    assert recs[0]["winner"] is None and recs[0]["hands"] == ["paper", "paper"]
    assert recs[1]["winner"] == 0 and recs[1]["hands"] == ["scissors", "paper"]
    assert seen_discard_with_draw["hand"] == h0   # 捨て札の選択時に勝ちドロー済み
    assert len(e.zlist("hand", 0)) == h0          # -1（出した）+1ドロー
    assert len(e.zlist("hand", 1)) == 1           # パー誘発2回分で2枚捨てた（2-2＋ターン2のドロー1枚）


def test_janken_hand_trigger_fires_on_other_cards_janken(rules):
    """他カードのジャンケンでも手の誘発が起きる（Wiki の例）: T753 のジャンケンで
    相手がパーを出すと、場の T756 のパー誘発も発動する。"""
    e = setup(rules, {"hand": ["T753"], "mana": ["T001", "T001", "T001"], "bz": ["T756"]},
              {"hand": ["T001", "T002"]})
    h0 = len(e.zlist("hand", 0))
    drv = _Driver(play=_play_once("play:T753"), choose=_first,
                  hands={0: ["rock"], 1: ["paper"]})
    drv.run(e, lambda ev: "T753" in _defns(ev, "bz", 0) and _quiet(ev)
            and len(e.zlist("hand", 1)) == 1)
    recs = [r for r in e.s.pub if r.get("kind") == "janken"]
    assert len(recs) == 1   # ジャンケン自体は1回だけ
    assert len(e.zlist("hand", 1)) == 1        # T753 のパー誘発: 相手が1枚捨てた
    assert len(e.zlist("hand", 0)) == h0       # T756 のパー誘発: 自分が1枚引いた（負けでドローなし分と相殺）


# ---------- 実挙動: T754（攻撃時ジャンケン＋チョキでマナブースト） ----------

def test_janken_attack_may_win_power_and_hand_mana(rules):
    """攻撃時: may でジャンケンし、勝ってパワー+5000。相手のチョキで山札の上をマナへ。"""
    e = setup(rules, {"bz": ["T754"], "mana": ["T005"]}, {"bz": []})
    m0 = len(e.zlist("mana", 0))
    drv = _Driver(attack=_attack_once("attack:T754:player"),
                  hands={0: ["rock"], 1: ["scissors"]})
    cid = _by_defn(e, "bz", 0)["T754"]

    def stop(ev):
        return (ev.chars_ro(cid)["power"] == 8000
                and len(ev.zlist("mana", 0)) == m0 + 1 and _quiet(ev))

    drv.run(e, stop)
    assert e.chars_ro(cid)["power"] == 8000
    assert len(e.zlist("mana", 0)) == m0 + 1


def test_janken_attack_may_decline_asks_nothing(rules):
    """攻撃時の may を断るとジャンケンしない（choose_one が出ない）。"""
    e = setup(rules, {"bz": ["T754"], "mana": ["T005"]}, {"bz": []})
    drv = _Driver(attack=_attack_once("attack:T754:player"), yes_no="no",
                  hands={0: ["rock"], 1: ["scissors"]})
    cid = _by_defn(e, "bz", 0)["T754"]
    drv.run(e, lambda ev: ev.chars_ro(cid)["power"] == 3000
            and "attack" in drv.seen_kinds and _quiet(ev))
    assert "choose_one" not in drv.seen_kinds
    assert e.chars_ro(cid)["power"] == 3000


# ---------- 実挙動: T755（バトル置換ジャンケン） ----------

def test_janken_battle_replace_attacker_wins(rules):
    """攻撃側が勝つ: バトルは起きず、負けた相手のバトル中クリーチャーが破壊される。"""
    e = setup(rules, {"bz": ["T755"]}, {"bz": ["T001"]})
    e.s.cards[_by_defn(e, "bz", 1)["T001"]].tapped = True   # 攻撃対象はタップ状態でなければならない
    drv = _Driver(attack=_attack_once("attack:T755:T001"),
                  hands={0: ["rock"], 1: ["scissors"]})
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T001" in _defns(e, "graveyard", 1)   # 相手のバトル中クリーチャーが破壊された
    assert "T755" in _defns(e, "bz", 0)          # 自分は生きている（バトルしていない）
    # 停止はターン2のチャージで初めて観測されるため e.s.turn は 2（バトルの後始末は
    # 決定を挟まず進む）。ジャンケン自体がターン1に起きたことは公開記録の turn で見る。
    recs = [r for r in e.s.pub if r.get("kind") == "janken"]
    assert len(recs) == 1 and recs[0]["turn"] == 1
    assert recs[0]["hands"] == ["rock", "scissors"] and recs[0]["winner"] == 0


def test_janken_battle_replace_attacker_loses_and_rock_draws(rules):
    """攻撃側が負ける: 自分のバトル中クリーチャーが破壊される。相手のグーで1ドロー。"""
    e = setup(rules, {"bz": ["T755"]}, {"bz": ["T001"]})
    e.s.cards[_by_defn(e, "bz", 1)["T001"]].tapped = True   # 攻撃対象はタップ状態でなければならない
    h0 = len(e.zlist("hand", 0))
    drv = _Driver(attack=_attack_once("attack:T755:T001"),
                  hands={0: ["scissors"], 1: ["rock"]})
    drv.run(e, lambda ev: "T755" in _defns(ev, "graveyard", 0) and _quiet(ev)
            and len(e.zlist("hand", 0)) == h0 + 1)
    assert "T755" in _defns(e, "graveyard", 0)
    assert "T001" in _defns(e, "bz", 1)          # 相手は生きている（バトルしていない）
    assert len(e.zlist("hand", 0)) == h0 + 1     # グー誘発で1ドロー


def test_janken_battle_replace_defender_wins(rules):
    """守備側が勝つ: 相手の攻撃クリーチャーが破壊され、バトルは起きない。"""
    e = setup(rules, {"bz": ["T755"]}, {"bz": ["T001"]})
    # T755 をフィクスチャでタップしても、p0 のターン1開始時のアンタップで戻される
    # （st_start はアクティブ・プレイヤーの bz をアンタップする）。p1 のターン2の
    # チャージ決定時にタップし直す — 攻撃ステップの選択肢が作られる前にタップが
    # 入るので、attack:T001:T755 が最初から選択肢に現れる（第230弾の遅延タップ）。
    t755 = _by_defn(e, "bz", 0)["T755"]

    def charge_p1(ev, d):
        if ev.s.turn == 2 and d["player"] == 1:
            ev.s.cards[t755].tapped = True
        return None

    # p1 のターンまで進め、T001 で T755 を攻撃させる
    drv = _Driver(attack=None, hands={0: ["rock"], 1: ["scissors"]}, charge=charge_p1)

    def attack_p1(e, d):
        keys = [o["key"] for o in d["options"]]
        hit = [i for i, k in enumerate(keys) if k == "attack:T001:T755"]
        return [hit[0]] if hit else None

    drv.attack = attack_p1
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T001" in _defns(e, "graveyard", 1)
    assert "T755" in _defns(e, "bz", 0)


# ---------- 実挙動: T757（クロスギアの宿主攻撃時ジャンケン） ----------

def test_janken_cross_gear_host_attack(rules):
    """ギアを生成してクロスし、宿主で攻撃する。勝ってマナからクリーチャーを出し、
    相手のチョキで山札の上をマナへ。"""
    e = setup(rules, {"hand": ["T757"], "mana": ["T001", "T001", "T001", "T001", "T001", "T001"],
                    "bz": ["T005"]},
              {"bz": []})
    m0 = len(e.zlist("mana", 0))

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        for want in ("play:T757", "cross:T757:T005"):
            if want in keys:
                return [keys.index(want)]
        return None

    drv = _Driver(play=play, attack=_attack_once("attack:T005:player"),
                  hands={0: ["rock"], 1: ["scissors"]})

    def stop(ev):
        g = _by_defn(ev, "bz", 0).get("T757")
        return (g is not None and ev.s.cards[g].crossed is not None
                and "T001" in _defns(ev, "bz", 0)
                and len(ev.zlist("mana", 0)) == m0 and _quiet(ev))

    drv.run(e, stop)
    g = _by_defn(e, "bz", 0)["T757"]
    host = _by_defn(e, "bz", 0)["T005"]
    assert list(e.s.cards[g].crossed) == list(e.s.ref(host))
    assert "T001" in _defns(e, "bz", 0)          # 勝ち: マナから出した
    assert len(e.zlist("mana", 0)) == m0         # -1（出した）+1（チョキ誘発）
