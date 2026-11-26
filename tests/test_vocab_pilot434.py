"""語彙パイロット第434弾: keyword_exists_condition（ドリフト）。

センサス（rejects 1,897件を取り直し）: pure 1,749件
（985家族）/ multi の gap 出現 268件 / 空 gaps 18件。
pure の大半は範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜433弾）は原則として再提案しない。残置群
（graveyard_replacement 残り dm25ex2-cho021、
battle_opponent_reference 残り dmr01-049、
untap_restriction 残り2件、does_not_untap 残り
dm25ex2-031、cast_limit_once_per_turn の multi 2件、
summoning_attack_rule 残り dmex07-s01、
entered_turn_attack 残り dmbd11-d05、madness 残り
dmx26-028、after_battle_trigger 残り dmrp09-074、
次点の destroyed_this_turn_condition /
count_cards_drawn_this_turn、後続候補の
distinct_civ_count、将来の新規語彙候補 first_time_tap /
turn_history_entry、専用ステージ送りの
power_threshold_keyword_gain）は覆す根拠が無く
再提案しない。本弾で個別に評価して見送った候補:
trigger_when_played_free（dm25ex4-t01。クリーチャー面は
第257弾の when {unpaid: true} で表せるが、ツインパクトの
呪文面が超次元で範囲外）、
trigger_when_entered_without_tapping_mana
（dm23bd6-005。クリーチャー面は unpaid で表せるが、
呪文面のパワー合計制約つき選択が未確立）、
played_free_condition（dm26sd1-i007。誘発内 if で
unpaid を参照する cond キーが無い。新規語彙候補として
残置）、first_attack_this_turn_condition（複合）、
trigger_when_drawn（手札ゾーンの引いた時誘発が未確立）、
ability_history_condition（自能力の履歴条件が未確立）、
name_exists_condition（2名合計＋instead の複合）、
same_cost_condition（look/reorder が未確立）、
block_trigger_attacker_filter（dm32-s09。ブロックされても
ブレイクさせる戦闘フロー変更が前提）、
attack_end_trigger（タマシードへの重ね置きが未確立）、
mana_tap_trigger（支払いタップのイベント化は影響が広い）、
untap_trigger / leave_trigger / attack_history /
tap_by_opponent_trigger（複合または原因帰属が未確立）。

範囲内・最小の **keyword_exists_condition（pure 1件、
multi にも現れない）** を選定した。行の注記「キーワード
所持の存在条件を表す語彙が無い」は陳腐化した評価で、
確立部品の組み合わせで表せる（ドリフト。新規語彙・
エンジン・defs・スキーマ変更なし）:
- 「バトルゾーンに「W・ブレイカー」を持つクリーチャーが
  あれば」は if {exists: {zone: bz, owner: any, filter:
  {types: [creature], keyword: double_breaker}}}。
  exists＋keyword フィルタは登録済み dmd05-015 /
  dmrp08-002 の確立形。selector の keyword 照合は付与分を
  含む現在特性で見るため、第398弾の static affects の
  base 照合制限はこの経路には及ばない。
- 「パワーは+5000され、「W・ブレイカー」を得る」は
  modify {select: {ref: self}, mod: {power: 5000,
  breaks: 2}, duration: end_of_turn}。power と breaks の
  併記は登録済み dm39-033 / dmsp01-012 / promoy5-037 の
  確立形。両条件が立てば power +16000 で、breaks は
  両方の能力が選択肢になり 509.2c で攻撃側が選ぶ
  （choose_breaker で breaks:2 / breaks:3 が提示される
  ことを本弾の実挙動で確認）。

対象は dmr07-010 マネコン（水 / コスト4 / パワー1000 /
種族 サイバーロード/アンノイズ / mana 1）。partial は
骨格のみで text は断片。**補完あり: text（公式全文）＋
abilities**。alias は無し（identity 実測で canon_id は
対象自身、aliases_for = []）。第434弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも対象 id は
登録なし。登録ブロッカーの確認（第375弾の教訓）:
rule_convert.split（対象行）は None を返し定型所有は
無い＝ツール側ブロッカーなし。単面カードで未検証の
面は無い。

結論はドリフト: abilities 2件 =
trigger {when: {event: attack, subject: self},
if: {exists: {zone: bz, owner: any, filter:
{types: [creature], keyword: double_breaker}}},
effect: [modify {select: {ref: self}, mod:
{power: 5000, breaks: 2}, duration: end_of_turn}]} と
T・ブレイカー版（power 11000 / breaks 3）。

proto T1223（dmr07-010 型）。判別役は本弾で追加した
T1224（W・ブレイカー持ち）/ T1225（T・ブレイカー持ち）と
既存の T001（キーワード無しバニラ）/ T004（パワー3000
ブロッカー）を流用する。

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

TRIG_W = {"kind": "trigger",
          "when": {"event": "attack", "subject": "self"},
          "if": {"exists": {"zone": "bz", "owner": "any",
                            "filter": {"types": ["creature"],
                                       "keyword": "double_breaker"}}},
          "effect": [{"op": "modify", "select": {"ref": "self"},
                      "mod": {"power": 5000, "breaks": 2},
                      "duration": "end_of_turn"}]}
TRIG_T = {"kind": "trigger",
          "when": {"event": "attack", "subject": "self"},
          "if": {"exists": {"zone": "bz", "owner": "any",
                            "filter": {"types": ["creature"],
                                       "keyword": "triple_breaker"}}},
          "effect": [{"op": "modify", "select": {"ref": "self"},
                      "mod": {"power": 11000, "breaks": 3},
                      "duration": "end_of_turn"}]}
FORM = [TRIG_W, TRIG_T]
FULL_TEXT = ("このクリーチャーが攻撃する時、バトルゾーンに"
             "「W・ブレイカー」を持つクリーチャーがあれば、そのターン、"
             "このクリーチャーのパワーは+5000され、「W・ブレイカー」を得る。\n"
             "このクリーチャーが攻撃する時、バトルゾーンに"
             "「T・ブレイカー」を持つクリーチャーがあれば、そのターン、"
             "このクリーチャーのパワーは+11000され、「T・ブレイカー」を得る。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1223")
    assert c["name"] == "マネコン"
    assert c["types"] == ["creature"] and c["civs"] == ["water"]
    assert c["cost"] == 4 and c["power"] == 1000 and c["mana"] == 1
    assert c["races"] == ["サイバーロード", "アンノイズ"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.abilities == FORM          # parse で形は変わらない
    for tid in ("T1224", "T1225", "T001", "T004"):
        parse_card(proto_card(tid), TABLES)
    assert proto_card("T1224")["keywords"] == ["double_breaker"]
    assert proto_card("T1225")["keywords"] == ["triple_breaker"]


def test_form_raw_parse():
    d = parse_card({"id": "TX434", "name": "マネコン",
                    "types": ["creature"], "civs": ["water"],
                    "cost": 4, "power": 1000, "mana": 1,
                    "races": ["サイバーロード", "アンノイズ"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert d.abilities == FORM


def _bad(mutate):
    c = {"id": "TX434B", "name": "x", "types": ["creature"],
         "civs": ["water"], "cost": 4, "power": 1000, "mana": 1,
         "abilities": copy.deepcopy(FORM)}
    mutate(c["abilities"][0])
    with pytest.raises(DefError):
        parse_card(c, TABLES)


def test_bad_forms_rejected():
    # filter の未知キーワードは DefError
    _bad(lambda a: a["if"]["exists"]["filter"].update(
        {"keyword": "no_such_keyword"}))
    # when の未知イベントは DefError
    _bad(lambda a: a.update(
        {"when": {"event": "attackk", "subject": "self"}}))
    # breaks の型違いは DefError
    _bad(lambda a: a["effect"][0].update(
        {"mod": {"power": 5000, "breaks": "x"}}))
    # effect の未知 op は DefError
    _bad(lambda a: a.update(
        {"effect": [{"op": "modifyy", "select": {"ref": "self"},
                     "mod": {"power": 5000}, "duration": "end_of_turn"}]}))


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


def _drive(e, attacker=None, blocker=None, stop=None, limit=900,
           breaker=None):
    """attacker（攻撃キー）を一度だけ攻撃させ、blocker
    （proto id）がいればブロックさせる。stop(e) が真に
    なるまで進める。発生源は召喚酔いがあるため、攻撃
    キーが現れるまで（次の自分のターンまで）進める。
    breaker を指定すると、複数のブレイカー能力を得た時の
    509.2c の選択（choose_breaker）でその枚数を選ぶ。"""
    st = {"attacked": False, "breaker_options": None}
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
        if d["kind"] == "choose_breaker":
            st["breaker_options"] = keys
            if breaker is not None and f"breaks:{breaker}" in keys:
                e.answer([keys.index(f"breaks:{breaker}")])
                continue
        _answer_default(e, d)
    return st


def test_w_breaker_present_breaks_two(rules):
    """W・ブレイカー持ちが場にいれば、攻撃時にパワー+5000・
    W・ブレイカーを得てシールドを2枚ブレイクする。"""
    e = _build(rules, {"bz": ["T1223", "T1224"]}, {"bz": []})
    src = _cid(e, 0, "T1223")
    st = _drive(e, attacker="attack:T1223:player",
                stop=lambda: len(e.zlist("shield", 1)) <= 3)
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 3    # 2枚ブレイク
    assert e.s.cards[src].zone == "bz"


def test_w_breaker_present_power_wins_battle(rules):
    """パワー判別: +5000 で 6000 になり、パワー3000の
    ブロッカーに勝つ（素のパワー1000では負ける）。"""
    e = _build(rules, {"bz": ["T1223", "T1224"]}, {"bz": ["T004"]})
    src = _cid(e, 0, "T1223")
    blk = _cid(e, 1, "T004")
    st = _drive(e, attacker="attack:T1223:player", blocker="T004",
                stop=lambda: e.s.cards[blk].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[blk].zone == "graveyard"
    assert e.s.cards[src].zone == "bz"
    assert len(e.zlist("shield", 1)) == 5    # ブロックされたので無傷


def test_t_breaker_present_breaks_three(rules):
    """T・ブレイカー持ちだけが場にいれば、パワー+11000・
    T・ブレイカーを得てシールドを3枚ブレイクする
    （triple_breaker は double_breaker 条件を満たさない）。"""
    e = _build(rules, {"bz": ["T1223", "T1225"]}, {"bz": []})
    src = _cid(e, 0, "T1223")
    st = _drive(e, attacker="attack:T1223:player",
                stop=lambda: len(e.zlist("shield", 1)) <= 2)
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 2    # 3枚ブレイク
    assert e.s.cards[src].zone == "bz"


def test_no_breaker_no_bonus(rules):
    """判別: ブレイカー持ちが場にいなければ何も得ず、
    ブレイクは1枚・パワーは素の1000のまま。"""
    e = _build(rules, {"bz": ["T1223", "T001"]}, {"bz": []})
    st = _drive(e, attacker="attack:T1223:player",
                stop=lambda: len(e.zlist("shield", 1)) <= 4)
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 4    # 1枚だけブレイク
    e2 = _build(rules, {"bz": ["T1223", "T001"]}, {"bz": ["T004"]})
    src = _cid(e2, 0, "T1223")
    st = _drive(e2, attacker="attack:T1223:player", blocker="T004",
                stop=lambda: e2.s.cards[src].zone == "graveyard")
    assert st["attacked"]
    assert e2.s.cards[src].zone == "graveyard"   # 1000 < 3000 で敗北


def test_opponent_w_breaker_counts(rules):
    """owner: any の判別: 相手の W・ブレイカー持ちでも
    条件を満たし、2枚ブレイクする。"""
    e = _build(rules, {"bz": ["T1223"]}, {"bz": ["T1224"]})
    st = _drive(e, attacker="attack:T1223:player",
                stop=lambda: len(e.zlist("shield", 1)) <= 3)
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 3


def test_both_present_breaker_choice(rules):
    """W と T の両方が場にいれば両方の誘発が立ち、使う
    ブレイカー能力は 509.2c で攻撃側が選ぶ（breaks:2 と
    breaks:3 の選択が提示される）。3を選べば3枚ブレイク。"""
    e = _build(rules, {"bz": ["T1223", "T1224", "T1225"]}, {"bz": []})
    st = _drive(e, attacker="attack:T1223:player", breaker=3,
                stop=lambda: len(e.zlist("shield", 1)) <= 2)
    assert st["attacked"]
    assert st["breaker_options"] == ["breaks:2", "breaks:3"]
    assert len(e.zlist("shield", 1)) == 2    # 3枚ブレイク
