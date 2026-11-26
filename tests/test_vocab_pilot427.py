"""語彙パイロット第427弾: turn_history_attacked（ドリフト）。

センサス（rejects 1,905件を取り直し）: pure 1,757件
（991家族）/ multi 130件 / 空 gaps 18件。pure の大半は
範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜426弾）は再提案しない。残置群（graveyard_
replacement 残り dm25ex2-cho021、battle_opponent_
reference 残り dmr01-049、untap_restriction 残り2件、
does_not_untap 残り dm25ex2-031、cast_limit_once_
per_turn の multi 2件、summoning_attack_rule 残り
dmex07-s01、entered_turn_attack 残り dmbd11-d05、
madness 残り dmx26-028、次点の destroyed_this_turn_
condition / count_cards_drawn_this_turn、後続候補の
distinct_civ_count、将来の新規語彙候補 first_time_
tap、専用ステージ送りの power_threshold_keyword_
gain）は覆す根拠が無く再提案しない。本弾で個別に
評価して見送った候補: flying（pure 2。dm26sd1-v007
は第3条項のタップ＝マナゾーン扱いが未確立、
dm26ex2-pr001 は追加ターン＋攻撃時誘発が未構築で、
どちらの行も飛行だけでは登録できない）、civ_blocker
（pure 2。文明限定ブロック適格＋その文明とのバトル
不破壊の2機構が要り最小でない）、attack_limit_once_
per_turn（pure 2。両行ともツインパクトで他の面・
条項が未構築）、power_set（pure 2。同名別刷り同士で
first_time 監視＋自己パワー条件 no_leave を含む
5条項の複合）、next_spell_cost_reduction（pure 3。
stub または複合条項つき）。

範囲内・最小の **turn_history_attacked（pure 1件、
multi にも現れない）** を選定した。行の注記「その
ターン攻撃したかどうかを判定する語彙が無い」は
履歴カウンタ基盤より前の陳腐化した評価で、確立部品
の組み合わせで表せる（ドリフト。新規語彙・エンジン・
defs・スキーマ変更なし）:
- 「そのターンこのクリーチャーが攻撃していたら」は
  turn_count {kind: attack_by, ref: self}。attack_by
  はクリーチャー単位の攻撃回数を数える確立式
  （第159・161弾。登録済み dm15-004 は attack_end
  誘発＋ attack_by == 1 で「このクリーチャーがこの
  ターンはじめて攻撃する時」を表現、ラウンド211）。
  所有者単位の kind: attack と違い、他のクリーチャー
  の攻撃では数えない点が文面との判別点。
- 「自分のターンの終わりに」は when {event:
  turn_end, player: you}（登録済み dm10-041 の
  確立形）。履歴の prev_counters への退避は次の
  ターンの st_start で行われるため、turn_end 誘発の
  if 評価時点では当ターンの hist:attack_by が
  生きている（turn.py 実測。本弾の実挙動でも判別）。
- 破壊は destroy {select: {ref: self}}（第413・
  422弾。parse で move {to: graveyard, reason:
  destroy} に正規化される）。

対象は dmd27-016 轟速 ザ・ゼット（火 / コスト4 /
パワー7000 / 種族 ソニック・コマンド/侵略者）。
公式テキスト: 「スピードアタッカー（この
クリーチャーは召喚酔いしない）W・ブレイカー
（このクリーチャーはシールドを２つブレイクする）
自分のターンの終わりに、そのターンこの
クリーチャーが攻撃していたら、破壊する。」
partial は骨格＋keywords [speed_attacker,
double_breaker] まで構築済みで text は公式全文
（補完なし）。alias は promoy15-052（partial の
source.aliases のみ、自前の reject 行は無い。
identity 実測で canon_id は対象自身、別刷りの
canon も対象、aliases_for = [promoy15-052]）。
第427弾時点で real.yaml / real_akashic.yaml /
real_vocab.yaml / real_zone.yaml / proto.yaml /
converted.yaml のいずれにも対象・別刷りとも
登録なし。登録ブロッカーの確認（第375弾の教訓）:
rule_convert.split（対象行）は (['speed_attacker',
'double_breaker'], 条項テキスト, []) を返し、
定型所有はキーワードのみで part[2] の能力所有は
空＝二重付着ブロッカー無し。単面カードで未検証の
面は無い。

結論はドリフト: abilities 1件 =
trigger {when: {event: turn_end, player: you},
if: {cmp: [{turn_count: {kind: attack_by,
ref: self}}, ">=", 1]}, effect: [destroy
{select: {ref: self}}]}。

proto T1205（dmd27-016 型）。判別役は既存 proto を
流用: T001（パワー2000バニラ＝他のクリーチャーだけが
攻撃した時の対照）/ T004（パワー3000ブロッカー＝
ブロックされてもバトルに勝てば条項が発火する判別）/
T1126（パワー8000ブロッカー＝バトルで破壊された
場合の対照）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の
作法）。
"""
import copy
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import (  # noqa: E402
    DefError, load_rules, load_tables, parse_card)
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()
ROOT = Path(__file__).parent.parent

TRIGGER = {"kind": "trigger",
           "when": {"event": "turn_end", "player": "you"},
           "if": {"cmp": [{"turn_count": {"kind": "attack_by",
                                          "ref": "self"}},
                          ">=", 1]},
           "effect": [{"op": "destroy", "select": {"ref": "self"}}]}
FORM = [TRIGGER]
PARSED_TRIGGER = {"kind": "trigger",
                  "when": {"event": "turn_end", "player": "you"},
                  "if": {"cmp": [{"turn_count": {"kind": "attack_by",
                                                 "ref": "self"}},
                                 ">=", 1]},
                  "effect": [{"op": "move", "select": {"ref": "self"},
                              "to": "graveyard", "reason": "destroy"}]}
FULL_TEXT = ("スピードアタッカー（このクリーチャーは召喚酔いしない）"
             "W・ブレイカー（このクリーチャーはシールドを２つブレイクする）"
             "自分のターンの終わりに、そのターンこのクリーチャーが"
             "攻撃していたら、破壊する。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1205")
    assert c["name"] == "轟速 ザ・ゼット"
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 4 and c["power"] == 7000 and c["mana"] == 1
    assert c["races"] == ["ソニック・コマンド", "侵略者"]
    assert c["keywords"] == ["speed_attacker", "double_breaker"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    # destroy は parse で move（to: graveyard, reason: destroy）に
    # 正規化される
    assert PARSED_TRIGGER in d.abilities
    for tid in ("T001", "T004", "T1126"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX427", "name": "轟速 ザ・ゼット",
                    "types": ["creature"], "civs": ["fire"],
                    "cost": 4, "power": 7000, "mana": 1,
                    "races": ["ソニック・コマンド", "侵略者"],
                    "keywords": ["speed_attacker", "double_breaker"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert PARSED_TRIGGER in d.abilities


def _bad(mutate):
    c = {"id": "TX427B", "name": "x", "types": ["creature"],
         "civs": ["fire"], "cost": 4, "power": 7000, "mana": 1,
         "abilities": copy.deepcopy(FORM)}
    mutate(c["abilities"][0])
    with pytest.raises(DefError):
        parse_card(c, TABLES)


def test_bad_forms_rejected():
    # attack_by には ref が必須
    _bad(lambda a: a["if"]["cmp"][0].update(
        {"turn_count": {"kind": "attack_by"}}))
    # attack_by に owner は付けられない（{kind, ref} のみ）
    _bad(lambda a: a["if"]["cmp"][0].update(
        {"turn_count": {"kind": "attack_by", "ref": "self",
                        "owner": "you"}}))
    # 未知の履歴 kind は DefError
    _bad(lambda a: a["if"]["cmp"][0].update(
        {"turn_count": {"kind": "attacked", "ref": "self"}}))
    # when の未知イベントは DefError
    _bad(lambda a: a.update(
        {"when": {"event": "turn_ended", "player": "you"}}))
    # effect の未知 op は DefError
    _bad(lambda a: a.update(
        {"effect": [{"op": "destroyy", "select": {"ref": "self"}}]}))


# ---------- 駆動ヘルパ ----------

def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn)


def _drive(e, attacker=None, blocker=None, stop=None, limit=600):
    """attacker（攻撃キー）を一度だけ攻撃させ、blocker
    （proto id）がいればブロックさせる。stop(e) が真に
    なるまで進める。"""
    st = {"attacked": False}
    for _ in range(limit):
        if stop and stop():
            return st
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if attacker and not st["attacked"] and d["kind"] == "attack" \
                and attacker in keys:
            e.answer([keys.index(attacker)])
            st["attacked"] = True
            continue
        if d["kind"] == "block" and blocker:
            hit = [i for i, k in enumerate(keys)
                   if k.startswith(f"bz:{blocker}")]
            if hit:
                e.answer([hit[0]])
                continue
        _answer_default(e, d)
    return st


def test_attacked_destroyed_at_own_turn_end(rules):
    """攻撃したら自分のターンの終わりに破壊される。
    W・ブレイカーでシールドは2枚ブレイクする。"""
    e = _build(rules, {"bz": ["T1205"]}, {"bz": []})
    src = _cid(e, 0, "T1205")
    st = _drive(e, attacker="attack:T1205:player",
                stop=lambda: e.s.cards[src].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[src].zone == "graveyard"
    assert len(e.zlist("shield", 1)) == 3


def test_not_attacked_survives_turn_end(rules):
    """攻撃しなければターンの終わりに破壊されない
    （相手ターンも1巡して自分の攻撃ステップに戻るまで
    場に残る。player: you の判別も兼ねる）。"""
    e = _build(rules, {"bz": ["T1205"]}, {"bz": []})
    src = _cid(e, 0, "T1205")
    seen = {"n": 0}
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if d["kind"] == "attack" and d.get("player") == 0:
            seen["n"] += 1
            if seen["n"] >= 2:   # 自分の2回目の攻撃ステップ
                break
        _answer_default(e, d)
    assert seen["n"] >= 2
    assert e.s.cards[src].zone == "bz"


def test_other_creature_attack_does_not_count(rules):
    """判別: 他の自分のクリーチャーだけが攻撃した場合は
    破壊されない（所有者単位の kind: attack ではなく
    attack_by {ref: self} で数えていることの確認）。"""
    e = _build(rules, {"bz": ["T1205", "T001"]}, {"bz": []})
    src = _cid(e, 0, "T1205")
    seen = {"n": 0}
    st = {"attacked": False}
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if not st["attacked"] and d["kind"] == "attack" \
                and "attack:T001:player" in keys:
            e.answer([keys.index("attack:T001:player")])
            st["attacked"] = True
            continue
        if d["kind"] == "attack" and d.get("player") == 0 \
                and st["attacked"]:
            seen["n"] += 1
            if seen["n"] >= 1:   # 次の自分の攻撃ステップ＝1巡した
                break
        _answer_default(e, d)
    assert st["attacked"]
    assert e.s.cards[src].zone == "bz"


def test_blocked_but_won_still_destroyed(rules):
    """ブロックされてバトルに勝っても「攻撃していた」
    ことに変わりはなく、ターンの終わりに破壊される。"""
    e = _build(rules, {"bz": ["T1205"]}, {"bz": ["T004"]})
    src = _cid(e, 0, "T1205")
    blk = _cid(e, 1, "T004")
    st = _drive(e, attacker="attack:T1205:player", blocker="T004",
                stop=lambda: e.s.cards[src].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[blk].zone == "graveyard"   # パワー3000はバトルで破壊
    assert e.s.cards[src].zone == "graveyard"   # ターン終了時に破壊
    assert len(e.zlist("shield", 1)) == 5       # ブロックされたので無傷


def test_destroyed_in_battle_stays_graveyard(rules):
    """対照: より強いブロッカーにバトルで破壊された場合は
    その時点で墓地にあり、ターン終了時に二重の処理は
    起きない（場に残らない）。"""
    e = _build(rules, {"bz": ["T1205"]}, {"bz": ["T1126"]})
    src = _cid(e, 0, "T1205")
    st = _drive(e, attacker="attack:T1205:player", blocker="T1126",
                stop=lambda: e.s.cards[src].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[src].zone == "graveyard"
    assert len(e.zlist("shield", 1)) == 5
