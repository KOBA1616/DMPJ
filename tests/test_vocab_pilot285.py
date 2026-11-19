"""語彙パイロット第285弾: free_play_event
（コストを支払わずに出したクリーチャーを破壊する）

rejects の free_play_event 純粋3件
（dmex10-006 ウソと盗みのエンターテイナー / dmex12-064 キャタピラ親方 /
dmsp01-033 早撃人形マグナム）。3件とも不足は「コストを支払わずに
バトルゾーンに出した時」という出来事を照合する語彙が無いという点だけ
で、partial の notes も「無料で出したことを照合する語彙が無い」と
書いている。しかしその照合は第257弾で入っている: when の unpaid は
両方のレコード構築経路（events._record_for と _apply_one）に伝播し、
(1) プレイ自体が無料の時（play タスクの free。G・ゼロ／S・トリガー
召喚／play_free の「使う」）と (2) 効果でバトルゾーンに出た時
（reason が summon でなく、bz の中での移動でない move）に立つ。
ラウンド291では同じ unpaid 誘発を持つ別ギャップ名の行が再変換済みで、
destroy {ref: event.subject} の形も登録先例がある。つまり本ファミリーは
ギャップ名のドリフトであり、本弾は新語彙・エンジン変更なしの
イディオム弾として、2つの subject 形を実挙動で固定する:

- 相手形（dmex10-006）: {kind: trigger,
  when: {event: move, to: bz, subject: {owner: opp,
  filter: {types: [creature]}}, unpaid: true},
  effect: [destroy {select: {ref: event.subject}}]}
- 全員形（dmsp01-033 / dmex12-064）: subject から owner を省く
  （_subject_match は owner が無い／"any" の時どちらにも一致する）。
  自分が効果で出した自分のクリーチャーも壊れるし、発生源自身が
  効果で出た時も自分を破壊する（原文「いずれかのプレイヤー」の
  とおり。本弾で実挙動を固定）。

境界も固定する: 通常召喚（支払った）は発火しない。コスト0の
クリーチャーを通常プレイしても「支払った」扱いで発火しない
（unpaid はプレイの free 印であって、コストの額ではない）。
タマシードは filter の types: [creature] で対象外（マグナム等の
原文はクリーチャーのみ）。

Rust: when に unpaid を含むため _simple_when の対象外
（_OK な when キーは event/from/to/reason/player/subject のみ）
で Python フォールバック。新規 GameState フィールドなし
（state.rs 変更なし）。スキーマ再生成なし（unpaid は when の
キーとして登録済み）。
"""
import pytest

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card
from dmsim.engine.rustcore import _simple_trigger
from tests.conftest import setup

TABLES = load_tables()

FORM_OPP = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp", "filter": {"types": ["creature"]}},
             "unpaid": True},
    "effect": [{"op": "destroy", "select": {"ref": "event.subject"}}],
}

FORM_ANY = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"filter": {"types": ["creature"]}},
             "unpaid": True},
    "effect": [{"op": "destroy", "select": {"ref": "event.subject"}}],
}

# destroy はマクロで move（to: graveyard, reason: destroy）に展開される
FORM_OPP_X = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp", "filter": {"types": ["creature"]}},
             "unpaid": True},
    "effect": [{"op": "move", "select": {"ref": "event.subject"},
                "to": "graveyard", "reason": "destroy"}],
}

FORM_ANY_X = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"filter": {"types": ["creature"]}},
             "unpaid": True},
    "effect": [{"op": "move", "select": {"ref": "event.subject"},
                "to": "graveyard", "reason": "destroy"}],
}


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """汎用ドライバ（第284弾のものと同じ）。"""

    def __init__(self, play=None, replace_seq=(), choose=None):
        self.play = play
        self.replace_seq = list(replace_seq)
        self.choose = choose
        self.seen = []

    def run(self, e, stop, limit=1200):
        for _ in range(limit):
            if e.s.result is not None:
                return
            d = e.advance()
            if d is None:
                return
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
            self.seen.append(kind)
            if kind == "choose_replacement":
                pol = self.replace_seq.pop(0) if self.replace_seq else "accept"
                if pol == "accept":
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


def _choose_targets(*defns):
    """choose_cards で、指定した defn のカードを順に選ぶフック。"""
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


# ---------- parse / validation ----------

def test_pilot285_protos_parse():
    rules = load_rules()
    assert rules.cards["T813"].abilities == [FORM_OPP_X]
    assert rules.cards["T814"].abilities == [FORM_ANY_X]
    # 生の辞書（destroy マクロ形）でも parse でき、展開形に一致する
    for i, (form, form_x) in enumerate(((FORM_OPP, FORM_OPP_X),
                                        (FORM_ANY, FORM_ANY_X))):
        d = parse_card({"id": f"TX285{i}", "name": "x", "types": ["creature"],
                        "civs": ["fire"], "cost": 4, "power": 3000,
                        "abilities": [form]}, TABLES)
        assert d.abilities == [form_x]
    # 未知のキーワードは弾かれる（語彙は閉じている）
    with pytest.raises(DefError):
        parse_card({"id": "TX285c", "name": "x", "types": ["creature"],
                    "civs": ["fire"], "cost": 4, "power": 3000,
                    "keywords": ["free_play_event"]}, TABLES)


def test_pilot285_not_rust_simple():
    # when に unpaid を含むため _simple_when の対象外（Python フォールバック）
    assert not _simple_trigger(dict(FORM_OPP_X))
    assert not _simple_trigger(dict(FORM_ANY_X))


# ---------- 実挙動: 相手形（T813） ----------

def test_813_destroys_opponent_effect_put(rules):
    """相手が効果でクリーチャーを出す（T815 の play_free）と破壊される。"""
    e = setup(rules, {"bz": ["T813"], "mana": ["T001"] * 3},
              {"hand": ["T815", "T816"], "mana": ["T010"] * 2})
    drv = _Driver(play=_play_times("play:T815", 1),
                  choose=_choose_targets("T816"))
    drv.run(e, lambda ev: "T816" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T816" in _defns(e, "graveyard", 1)
    assert "T816" not in _defns(e, "bz", 1)


def test_813_ignores_opponent_paid_summon(rules):
    """相手の通常召喚（コストを支払った）には発火しない。"""
    e = setup(rules, {"bz": ["T813"], "mana": ["T001"] * 3},
              {"hand": ["T816"], "mana": ["T001"] * 3})
    drv = _Driver(play=_play_times("play:T816", 1))
    drv.run(e, lambda ev: "T816" in _defns(ev, "bz", 1) and _quiet(ev))
    assert "T816" in _defns(e, "bz", 1)
    assert "T816" not in _defns(e, "graveyard", 1)


def test_813_destroys_opponent_free_action(rules):
    """相手が無料プレイの選択肢（G・ゼロ形 T818）で出すと破壊される
    （play タスクの free 印 → unpaid の経路）。"""
    e = setup(rules, {"bz": ["T813"], "mana": ["T001"] * 3},
              {"bz": ["T816"], "hand": ["T818"], "mana": ["T034"] * 2})
    drv = _Driver(play=_play_times("play:T818:free", 1))
    drv.run(e, lambda ev: "T818" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T818" in _defns(e, "graveyard", 1)
    assert "T816" in _defns(e, "bz", 1)   # 先にいた獣は無事


def test_813_ignores_own_effect_put(rules):
    """相手形は自分の効果出しには発火しない（subject の owner: opp）。"""
    e = setup(rules, {"bz": ["T813"], "hand": ["T815", "T816"],
                      "mana": ["T010"] * 2},
              {"mana": ["T001"] * 3})
    drv = _Driver(play=_play_times("play:T815", 1),
                  choose=_choose_targets("T816"))
    drv.run(e, lambda ev: "T816" in _defns(ev, "bz", 0) and _quiet(ev))
    assert "T816" in _defns(e, "bz", 0)
    assert "T816" not in _defns(e, "graveyard", 0)


def test_813_ignores_unpaid_tamaseed(rules):
    """タマシードを効果で出しても発火しない（filter は creature のみ）。"""
    e = setup(rules, {"bz": ["T813"], "mana": ["T001"] * 3},
              {"hand": ["T819", "T811"], "mana": ["T001"] * 2})
    drv = _Driver(play=_play_times("play:T819", 1),
                  choose=_choose_targets("T811"))
    drv.run(e, lambda ev: "T811" in _defns(ev, "bz", 1) and _quiet(ev))
    assert "T811" in _defns(e, "bz", 1)
    assert "T811" not in _defns(e, "graveyard", 1)


def test_813_ignores_paid_zero_cost(rules):
    """コスト0のクリーチャーを通常プレイしても「支払った」扱いで
    発火しない（unpaid は額ではなくプレイの free 印）。"""
    e = setup(rules, {"bz": ["T813"], "mana": ["T001"] * 3},
              {"hand": ["T817"], "mana": ["T001"] * 3})
    drv = _Driver(play=_play_times("play:T817", 1))
    drv.run(e, lambda ev: "T817" in _defns(ev, "bz", 1) and _quiet(ev))
    assert "T817" in _defns(e, "bz", 1)
    assert "T817" not in _defns(e, "graveyard", 1)


# ---------- 実挙動: 全員形（T814） ----------

def test_814_destroys_own_effect_put(rules):
    """全員形は自分の効果出しにも発火する（「いずれかのプレイヤー」）。"""
    e = setup(rules, {"bz": ["T814"], "hand": ["T815", "T816"],
                      "mana": ["T010"] * 2},
              {"mana": ["T001"] * 3})
    drv = _Driver(play=_play_times("play:T815", 1),
                  choose=_choose_targets("T816"))
    drv.run(e, lambda ev: "T816" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "T816" in _defns(e, "graveyard", 0)
    assert "T816" not in _defns(e, "bz", 0)
    assert "T814" in _defns(e, "bz", 0)   # 発生源は残る


def test_814_destroys_opponent_effect_put(rules):
    """全員形は相手の効果出しにも発火する。"""
    e = setup(rules, {"bz": ["T814"], "mana": ["T001"] * 3},
              {"hand": ["T815", "T816"], "mana": ["T010"] * 2})
    drv = _Driver(play=_play_times("play:T815", 1),
                  choose=_choose_targets("T816"))
    drv.run(e, lambda ev: "T816" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T816" in _defns(e, "graveyard", 1)
    assert "T816" not in _defns(e, "bz", 1)


def test_814_ignores_opponent_paid_summon(rules):
    """全員形でも通常召喚には発火しない。"""
    e = setup(rules, {"bz": ["T814"], "mana": ["T001"] * 3},
              {"hand": ["T816"], "mana": ["T001"] * 3})
    drv = _Driver(play=_play_times("play:T816", 1))
    drv.run(e, lambda ev: "T816" in _defns(ev, "bz", 1) and _quiet(ev))
    assert "T816" in _defns(e, "bz", 1)
    assert "T816" not in _defns(e, "graveyard", 1)


def test_814_self_entry_destroys_itself(rules):
    """発生源自身が効果で出た時、その誘発は自身を破壊する
    （原文「いずれかのプレイヤーが…出した時、そのクリーチャーを
    破壊する」の素直な読み。誘発の収集は移動後の bz を見る）。"""
    e = setup(rules, {"mana": ["T001"] * 3},
              {"bz": ["T816"], "hand": ["T815", "T814"], "mana": ["T010"] * 2})
    drv = _Driver(play=_play_times("play:T815", 1),
                  choose=_choose_targets("T814"))
    drv.run(e, lambda ev: "T815" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T814" in _defns(e, "graveyard", 1)
    assert "T814" not in _defns(e, "bz", 1)
    assert "T816" in _defns(e, "bz", 1)   # 先にいた獣は無事
