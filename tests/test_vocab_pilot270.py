"""語彙パイロット第270弾: ability_copy（他者の誘発能力の使用）。

「相手のターンに相手のクリーチャーが出て、その能力がトリガーした時、
自分もその能力を使ってもよい」（魔誕の斬将オルゲイト）。

新語彙は2つ。(1) イベント **`trigger`**: 自身の出た時能力（move→bz、
subject self）が誘発したことを、_collect_triggers が発表する。
観測型の誘発や trigger イベント自体を見る能力は発表しないので再帰しない。
(2) op **`use_triggered_ability`**（引数なし）: env.event の trigger
レコードが指す能力（ability）を、使う側の能力として解決する。
self は使う側のまま、event.subject も使う側に差し替える
（第261弾の use_entry_abilities と同型）。

「その能力」は誘発した1つの能力だけを指す。複数ある出た時能力は
能力ごとに trigger イベントが発表され、それぞれ別にコピーできる。
Rust の _simple_when は event "trigger" を知らないため、この能力を
持つカードを含む対局は Python にフォールバックする。
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


class _Driver:
    """汎用ドライバ（第268弾のものを流用）。seen_kinds に出た決定種を記録する。"""

    def __init__(self, play=None, choose=None, yes_no="yes", attack=None):
        self.play = play
        self.choose = choose
        self.yes_no = yes_no
        self.attack = attack
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


def _pick_t001_else_first(e, d):
    idx = [i for i, o in enumerate(d["options"])
           if e.s.cards[o["cid"]].defn == "T001"]
    if idx:
        return idx[:1]
    return [0]


def _no_effect_tasks(e):
    return not any(t.get("t") == "effect" for t in e.s.tasks)


# ---------- parse / validation ----------

def test_pilot270_protos_parse():
    rules = load_rules()
    t749 = rules.cards["T749"]
    assert t749.abilities[0]["when"] == {
        "event": "trigger",
        "subject": {"owner": "opp", "filter": {"types": ["creature"]}}}
    assert t749.abilities[0]["if"] == {"is_turn": "opp"}
    assert t749.abilities[0]["effect"] == [
        {"op": "may", "body": [{"op": "use_triggered_ability"}]}]
    assert rules.cards["T748"].abilities[0]["effect"] == [
        {"op": "draw", "count": 1}]
    base = {"id": "TX", "name": "x", "types": ["creature"],
            "civs": ["water"], "cost": 4, "power": 3000, "races": ["テスト"],
            "abilities": [{"kind": "trigger",
                           "when": {"event": "trigger",
                                    "subject": {"owner": "opp",
                                                "filter": {"types": ["creature"]}}},
                           "if": {"is_turn": "opp"},
                           "effect": [{"op": "may", "body": [{"op": "use_triggered_ability"}]}]}]}
    parse_card(dict(base), TABLES)
    with pytest.raises(DefError):
        bad = dict(base)
        bad["abilities"] = [{"kind": "trigger",
                             "when": {"event": "triggered"},
                             "effect": [{"op": "draw", "count": 1}]}]
        parse_card(bad, TABLES)
    with pytest.raises(DefError):
        bad = dict(base)
        bad["abilities"] = [{"kind": "trigger",
                             "when": {"event": "move", "to": "bz", "subject": "self"},
                             "effect": [{"op": "use_triggered_ability_xyz"}]}]
        parse_card(bad, TABLES)


def test_pilot270_trigger_event_not_rust_simple():
    """event "trigger" を持つ誘発は Rust の単純条件に入らない（Python へフォールバック）。"""
    assert not _simple_when({"event": "trigger",
                             "subject": {"owner": "opp", "filter": {"types": ["creature"]}}})
    assert _simple_when({"event": "move", "to": "bz", "subject": "self"})


# ---------- 実挙動 ----------

def test_copy_draw_on_opponent_turn(rules):
    """相手のターンに相手クリーチャーが出て CIP が誘発したら、コピー側も1枚引ける。"""
    e = setup(rules, {"hand": ["T748"], "mana": ["T001"] * 3},
              {"bz": ["T749"]})
    drv = _Driver(play=_play_once("play:T748"))

    def stop(ev):
        # コピーしたドローが解決した直後、p1 のターン開始ドローも済んだ
        # チャージ決定で止める（手札1 == コピー1 + ターンドロー1）。
        return (len(ev.zlist("hand", 1)) >= 1 and _no_effect_tasks(ev)
                and "T748" in _defns(ev, "bz", 0) and not ev.s.pending)

    drv.run(e, stop)
    assert "T748" in _defns(e, "bz", 0)
    assert len(e.zlist("hand", 0)) == 1   # 自分の CIP のドロー
    assert len(e.zlist("hand", 1)) == 2   # コピーした CIP 1 + p1 のターンドロー1
    assert "yes_no" in drv.seen_kinds


def test_copy_draw_decline(rules):
    """may を断れば、コピー側は引かない（元の CIP だけ解決する）。"""
    e = setup(rules, {"hand": ["T748"], "mana": ["T001"] * 3},
              {"bz": ["T749"]})
    drv = _Driver(play=_play_once("play:T748"), yes_no="no")

    def stop(ev):
        return ("T748" in _defns(ev, "bz", 0) and _no_effect_tasks(ev)
                and not ev.s.pending and len(ev.zlist("hand", 0)) == 1)

    drv.run(e, stop)
    assert len(e.zlist("hand", 0)) == 1   # 自分の CIP のドロー
    assert len(e.zlist("hand", 1)) == 1   # p1 のターンドローのみ（コピーなし）
    assert "yes_no" in drv.seen_kinds


def test_no_copy_for_own_creature(rules):
    """自分のクリーチャーが出た時はコピーしない（subject owner: opp）。"""
    e = setup(rules, {"hand": ["T748"], "bz": ["T749"], "mana": ["T001"] * 3}, {})
    drv = _Driver(play=_play_once("play:T748"))

    def stop(ev):
        return ("attack" in drv.seen_kinds
                and "T748" in _defns(ev, "bz", 0) and _no_effect_tasks(ev))

    drv.run(e, stop)
    assert len(e.zlist("hand", 0)) == 1   # 自分の CIP のドローのみ
    assert "yes_no" not in drv.seen_kinds


def test_no_copy_when_entry_on_own_turn(rules):
    """自分のターンに相手クリーチャーが出てもコピーしない（if is_turn: opp）。"""
    e = setup(rules, {"hand": ["T751"], "bz": ["T749"], "mana": ["T003"] * 2},
              {"hand": ["T748"]})
    drv = _Driver(play=_play_once("play:T751"))

    def stop(ev):
        return ("attack" in drv.seen_kinds
                and "T748" in _defns(ev, "bz", 1) and _no_effect_tasks(ev))

    drv.run(e, stop)
    assert "T748" in _defns(e, "bz", 1)
    assert len(e.zlist("hand", 1)) == 1   # 出た本人の CIP のドローのみ
    assert "yes_no" not in drv.seen_kinds


def test_copy_targeted_destroy_uses_copier_side(rules):
    """対象を取る CIP をコピーすると、選ぶ側はコピーした側になる。"""
    e = setup(rules, {"hand": ["T750"], "mana": ["T750"] * 5},
              {"bz": ["T749", "T001"]})
    drv = _Driver(play=_play_once("play:T750"),
                  choose=_pick_t001_else_first)

    def stop(ev):
        return (_no_effect_tasks(ev)
                and "T001" in _defns(ev, "graveyard", 1)
                and "T750" in _defns(ev, "graveyard", 0))

    drv.run(e, stop)
    assert "T001" in _defns(e, "graveyard", 1)   # 元の CIP で破壊
    assert "T750" in _defns(e, "graveyard", 0)   # コピーした CIP で破壊
    assert "yes_no" in drv.seen_kinds


def test_no_copy_for_attack_trigger(rules):
    """出た時でない誘発（攻撃時）は trigger イベントにならず、コピーしない。"""
    e = setup(rules, {"bz": ["T752"]}, {"bz": ["T749"]})

    def attack(e, d):
        keys = [o["key"] for o in d["options"]]
        hit = [i for i, k in enumerate(keys) if k == "attack:T752:player"]
        return hit[:1] if hit else None

    drv = _Driver(attack=attack)

    def stop(ev):
        return ("choose_shields" in drv.seen_kinds
                and len(ev.zlist("hand", 0)) == 1 and _no_effect_tasks(ev))

    drv.run(e, stop)
    assert len(e.zlist("hand", 0)) == 1   # 攻撃時誘発のドローのみ
    assert "yes_no" not in drv.seen_kinds
