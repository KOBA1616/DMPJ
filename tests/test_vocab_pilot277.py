"""語彙パイロット第277弾: true_escape（真・エスケープ）。

rejects の true_escape 純粋3件はいずれもキーワード「真・エスケープ」だけが不足:
- dm23rp2x-010 アウルーリー-T8（＋「自分のシールドがなければ離れない」条項）
- dm24bd5-004 聖霊妖精オーデマリー
- dm24rp1-011 獲銀月 ミール（ハイパー時のみ）

真・エスケープ = 「このクリーチャーが離れる時、かわりに自分のシールドを
2つ手札に加えてもよい。ただし、その『S・トリガー』は使えない」。
既存の escape（破壊時のみ・1枚）と eternal_omega（離れる時全般・強制）の
中間で、置換の機構そのものは両者の先例で実証済み。本弾の新規は
keywords.yaml へのキーワード追加のみ（エンジンのコードは変えない、
という keywords.yaml 冒頭の原則どおり）:

- when: {event: move, from: bz, subject: self}（eternal_omega と同じ
  「離れる時」全般。行き先・理由は問わない）
- if: {cmp: [{count: {zone: shield, owner: you}}, ">=", 2]}
  （2枚払える時だけ諮問する。escape の exists は「1枚以上」しか表せず、
  1枚しか無い時に諮問して選ばせると支払えない置換になるため cmp/count）
- instead: シールド2枚を手札へ（reason: return、strigger: "off" は
  escape と同形。その「S・トリガー」は使えない）

dm23rp2x-010 の「自分のシールドがなければ、このクリーチャーは離れない」は
キーワードの外の条項で、既存の mod no_leave を常在型の if でゲートする形
（{kind: static, affects: self, if: {not: {exists: {zone: shield,
owner: you}}}, mod: {no_leave: true}}）で表せることを T786 で検証する。
シールドが1枚あれば no_leave は切れ、真・エスケープも2枚払えず通常どおり
離れる（原文の境界どおり）。

dm24rp1-011 の真・エスケープはハイパー時のみ。mod grant は置換能力を
届けない（abilities() が展開するのは印刷キーワードと mod.gain だけ）ため、
ラウンド312ではキーワード本体を mod.gain で {hyper: true} ゲートする形
（第240弾のセイバー付与と同型）を使う。検証は cards テスト側。

Rust: true_escape は _OK_KW になく、置換も _simple_replace が弾く
（escape と同じ）ため、この能力を持つカードを含む対局は Python に
フォールバックする。新しい GameState フィールドは無い（state.rs 変更なし）。
スキーマはキーワード enum の追加で再生成した。
"""
import pytest
from tests.conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card
from dmsim.engine.rustcore import _OK_KW, _simple_replace

TABLES = load_tables()

EXPECTED_AB = {
    "kind": "replace", "optional": True,
    "when": {"event": "move", "from": "bz", "subject": "self"},
    "if": {"cmp": [{"count": {"zone": "shield", "owner": "you"}}, ">=", 2]},
    "instead": [{"op": "move",
                 "select": {"zone": "shield", "owner": "you", "count": 2},
                 "to": "hand", "reason": "return", "strigger": "off"}],
}


def _defns(e, zone, p):
    # zlist("bz", p) は共有ゾーンで両軍分を含むため、バトルゾーンは bz_tops で絞る
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """汎用ドライバ（第271/272弾のものに置換ポリシーを追加）。

    replace: "accept" なら choose_replacement で replace: を選び、
    "decline" なら decline を選ぶ。seen に全決定種別を記録する。
    choose: choose_cards へのフック (e, d) -> 答えのリストか None。
    """

    def __init__(self, play=None, attack=None, replace="accept", choose=None):
        self.play = play
        self.attack = attack
        self.replace = replace
        self.choose = choose
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


def _attack_once(key):
    seen = {}

    def attack(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and not seen.get("opt"):
            seen["opt"] = True
            return [keys.index(key)]
        return None

    return attack


# ---------- parse / validation ----------

def test_pilot277_protos_parse():
    rules = load_rules()
    t785 = rules.cards["T785"]
    assert "true_escape" in t785.keywords
    abs_te = [ab for ab in t785.abilities if ab.get("keyword") == "true_escape"]
    assert len(abs_te) == 1
    assert {k: abs_te[0][k] for k in EXPECTED_AB} == EXPECTED_AB
    t786 = rules.cards["T786"]
    assert "true_escape" in t786.keywords
    statics = [ab for ab in t786.abilities if ab["kind"] == "static"]
    assert {"kind": "static", "affects": "self",
            "if": {"not": {"exists": {"zone": "shield", "owner": "you"}}},
            "mod": {"no_leave": True}} in statics
    # 生の辞書でもキーワード展開される
    d = parse_card({"id": "TX277", "name": "x", "types": ["creature"],
                    "civs": ["light"], "cost": 5, "power": 2000,
                    "keywords": ["true_escape"]}, TABLES)
    assert [ab for ab in d.abilities if ab.get("keyword") == "true_escape"]
    # 未知のキーワードは弾かれる（語彙は閉じている）
    with pytest.raises(DefError):
        parse_card({"id": "TX278", "name": "x", "types": ["creature"],
                    "civs": ["light"], "cost": 5, "power": 2000,
                    "keywords": ["true_escape_x"]}, TABLES)


def test_pilot277_not_rust_simple():
    # escape と同様、Rust はこのキーワードと置換を知らない → Python フォールバック
    assert "true_escape" not in _OK_KW
    assert not _simple_replace(dict(EXPECTED_AB))


# ---------- 実挙動: T785（真・エスケープ） ----------

def test_true_escape_replaces_destroy(rules):
    """破壊される時、かわりにシールド2枚を手札に加え、クリーチャーは残る。"""
    e = setup(rules, {"bz": ["T785"]}, {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"))
    drv.run(e, lambda ev: "T785" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 3 and _quiet(ev))
    assert "T785" in _defns(e, "bz", 0)
    assert "T785" not in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == 3
    # 手札3枚 = 支払ったシールド2枚＋次の自分のターンのドロー1枚
    # （解決から次の決定までにターン境界を越える。第271弾の教訓）
    assert _defns(e, "hand", 0) == ["T001", "T001", "T001"]
    assert "T056" in _defns(e, "graveyard", 1)
    assert drv.seen.count("choose_replacement") == 1


def test_true_escape_moved_shields_cannot_strigger(rules):
    """手札に加えたシールドは「S・トリガー」を使えない（strigger: "off" の印）。"""
    e = setup(rules, {"bz": ["T785"],
                      "shield": ["T207", "T207", "T001", "T001", "T001"]},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    t207s = [c for c in e.zlist("shield", 0) if e.cdef(c).id == "T207"]
    assert len(t207s) == 2

    def choose(ev, d):
        hit = [i for i, o in enumerate(d["options"]) if o["cid"] in t207s]
        return hit[:d.get("min", 0)] or None

    drv = _Driver(play=_play_once("play:T056"), choose=choose)
    drv.run(e, lambda ev: all(ev.s.cards[c].zone == "hand" for c in t207s)
            and _quiet(ev))
    assert all(e.s.cards[c].zone == "hand" for c in t207s)
    assert all(e.s.cards[c].strigger_off is True for c in t207s)
    assert "declare_strigger" not in drv.seen
    assert "T785" in _defns(e, "bz", 0)


def test_true_escape_declined(rules):
    """辞退すれば通常どおり破壊される。シールドは減らない。"""
    e = setup(rules, {"bz": ["T785"]}, {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"), replace="decline")
    drv.run(e, lambda ev: "T785" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "T785" in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == 5
    assert drv.seen.count("choose_replacement") == 1


def test_true_escape_replaces_bounce(rules):
    """「離れる時」全般: 手札に戻す効果も置換できる（行き先は問わない）。"""
    e = setup(rules, {"bz": ["T785"]}, {"hand": ["T140"], "mana": ["T140"] * 3})
    drv = _Driver(play=_play_once("play:T140"))
    drv.run(e, lambda ev: "T785" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 3 and _quiet(ev))
    assert "T785" in _defns(e, "bz", 0)
    assert "T785" not in _defns(e, "hand", 0)
    assert _defns(e, "hand", 0) == ["T001", "T001", "T001"]   # 支払2枚＋ドロー1枚
    assert len(e.zlist("shield", 0)) == 3


def test_true_escape_battle_loss(rules):
    """バトルで負けて破壊される時も置換できる。"""
    e = setup(rules, {"bz": ["T004"]}, {"bz": ["T785"]})
    cid = next(c for c in e.bz_tops(1) if e.cdef(c).id == "T785")
    e.s.cards[cid].tapped = True
    drv = _Driver(attack=_attack_once("attack:T004:T785"))
    drv.run(e, lambda ev: "T785" in _defns(ev, "bz", 1)
            and len(ev.zlist("shield", 1)) == 3 and _quiet(ev))
    assert "T785" in _defns(e, "bz", 1)
    assert "T785" not in _defns(e, "graveyard", 1)
    assert len(e.zlist("shield", 1)) == 3
    assert drv.seen.count("choose_replacement") == 1


def test_true_escape_unavailable_with_one_shield(rules):
    """シールド1枚では2枚払えないため、諮問自体が起きず破壊される。"""
    e = setup(rules, {"bz": ["T785"], "shield": ["T001"]},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"))
    drv.run(e, lambda ev: "T785" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "T785" in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == 1
    assert "choose_replacement" not in drv.seen


def test_true_escape_unavailable_without_shields(rules):
    e = setup(rules, {"bz": ["T785"], "shield": []},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"))
    drv.run(e, lambda ev: "T785" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "T785" in _defns(e, "graveyard", 0)
    assert "choose_replacement" not in drv.seen


def test_true_escape_mass_destroy_two_saved(rules):
    """全体破壊（2体）: 両方とも諮問され、2枚ずつ払って両方残る（5枚→1枚）。

    なお同時離脱では、エンジンの置換は全件の諮問を instead の支払いより
    先に済ませる（capture 相。escape 等の既存置換と共通の構造）ため、
    if の枚数判定は諮問時点の枚数で読まれる。本テストの範囲（2体・5枚）
    では逐次処理と結果は一致する。"""
    e = setup(rules, {"bz": ["T785"] * 2}, {"hand": ["T500"], "mana": ["T500"] * 5})
    drv = _Driver(play=_play_once("play:T500"))
    drv.run(e, lambda ev: _defns(ev, "bz", 0).count("T785") == 2
            and len(ev.zlist("shield", 0)) == 1 and _quiet(ev))
    assert _defns(e, "bz", 0).count("T785") == 2
    assert _defns(e, "graveyard", 0).count("T785") == 0
    assert len(e.zlist("shield", 0)) == 1
    assert len(e.zlist("hand", 0)) == 5   # 支払4枚＋ドロー1枚
    assert drv.seen.count("choose_replacement") == 2


# ---------- 実挙動: T786（真・エスケープ＋シールドがなければ離れない） ----------

def test_no_leave_blocks_destroy_without_shields(rules):
    """シールドがなければ離れない: 破壊呪文が当たってもバトルゾーンに残る。"""
    e = setup(rules, {"bz": ["T786"], "shield": []},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"))
    drv.run(e, lambda ev: "T056" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T786" in _defns(e, "bz", 0)
    assert "T786" not in _defns(e, "graveyard", 0)
    assert len(e.zlist("hand", 0)) == 1   # 次の自分のターンのドローのみ（支払いは無い）
    assert "choose_replacement" not in drv.seen


def test_no_leave_boundary_with_one_shield(rules):
    """シールド1枚: no_leave は切れるが真・エスケープは払えない → 通常どおり破壊。"""
    e = setup(rules, {"bz": ["T786"], "shield": ["T001"]},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"))
    drv.run(e, lambda ev: "T786" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "T786" in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == 1
    assert "choose_replacement" not in drv.seen


def test_no_leave_off_and_true_escape_with_shields(rules):
    """シールドがあれば no_leave は切れ、真・エスケープの諮問が起きる。"""
    e = setup(rules, {"bz": ["T786"]}, {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"))
    drv.run(e, lambda ev: "T786" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 3 and _quiet(ev))
    assert "T786" in _defns(e, "bz", 0)
    assert len(e.zlist("shield", 0)) == 3
    assert _defns(e, "hand", 0) == ["T001", "T001", "T001"]   # 支払2枚＋ドロー1枚
    assert drv.seen.count("choose_replacement") == 1
