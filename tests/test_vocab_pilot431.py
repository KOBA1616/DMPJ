"""語彙パイロット第431弾: after_battle_trigger（ドリフト）。

センサス（rejects 1,900件を取り直し）: pure 1,752件
（987家族）/ multi 130件 / 空 gaps 18件。pure の大半は
範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜430弾）は原則として再提案しない。残置群
（graveyard_replacement 残り dm25ex2-cho021、
battle_opponent_reference 残り dmr01-049、
untap_restriction 残り2件、does_not_untap 残り
dm25ex2-031、cast_limit_once_per_turn の multi 2件、
summoning_attack_rule 残り dmex07-s01、
entered_turn_attack 残り dmbd11-d05、madness 残り
dmx26-028、次点の destroyed_this_turn_condition /
count_cards_drawn_this_turn、後続候補の
distinct_civ_count、将来の新規語彙候補 first_time_tap /
turn_history_entry、専用ステージ送りの
power_threshold_keyword_gain）は覆す根拠が無く
再提案しない。本弾で個別に評価して見送った候補:
same_name_count（dm28-006。状態条件での自己破壊は
継続チェックが前提で第362弾却下の
state_condition_destruction と同根）、no_untap_rule
（dmex08-207。はじめのドロー誘発＋マナ3枚タップ費用が
未検証で最小でない）、turn_draw_trigger（dm14-039。
第359弾どおりターン開始ドローの区別照合が無い）、
shield_event_condition（2件。シールドが墓地に置かれた
ターンの履歴照合が未確立）、enters_tapped_optional
（2件。第323弾で却下済み）。

範囲内・最小の **after_battle_trigger（pure 2件、
multi にも現れない）のうち dmrp14-072 のみ** を選定
した。本ファミリーは第359弾で「dmrp09-074 は勝者
参照が要り、dmrp14-072 は自己破壊で形が相異なり
均一な小語彙にならない」として見送られたが、これは
ファミリーの均一性への異議であり dmrp14-072 自体の
表現不能の所見ではない。形の異なる pure 2件から
表現可能な側だけを取る進め方は第386・388・400・
407・411・420弾で常例化し、本件の形については
第359弾以降の新しい証拠がある（覆し）:
- 登録済み dmpcd03-b11 邪眼銃士ディミトリ卿が本件と
  同一の条項構造（ブロッカー／攻撃できない／
  「バトルする時、バトルの後、破壊する」）を
  trigger {when: {event: battle_end, subject: self},
  effect: [destroy {select: {ref: self}}]} ＋
  keywords [blocker, cannot_attack] で登録済み。
  その notes には旧形（攻撃誘発＋delayed_trigger）が
  攻撃できないクリーチャーでは発火せず、修繕
  ステージで第211弾の battle_end 誘発に差し替えた
  経緯が残る。
- 第423弾で battle_end レコード（両参加者を subject
  とする）も実測済み。攻撃側の同一文面は登録済み
  dmbd16-teki005（ラウンド247）が同じ形で保持する。
もう1件の dmrp09-074（勝ったクリーチャーを手札に
戻す）は勝者参照が要るため残置し、ファミリーは
解消しない。

対象は dmrp14-072 血誓怪人ザミザニン（闇 / コスト2 /
パワー5000 / 種族 デビルマスク / mana 1）。対象行は
partial も reason フィールドも無い素行（第393・
415・416弾と同型）で、骨格は公式データ行
（by_product/rp14.jsonl）から決定的に構築した。
text は公式全文（補完なし）。alias は無し
（identity 実測で canon_id は対象自身、
aliases_for = []）。第431弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも対象 id は
登録なし。登録ブロッカーの確認（第375弾の教訓）:
rule_convert.split（対象行）は (['blocker',
'cannot_attack'], 条項テキスト, []) を返し、定型所有は
キーワード2件のみで part[2] の能力所有は空＝
二重付着ブロッカー無し。単面カードで未検証の面は無い。

結論はドリフト: abilities 1件 =
trigger {when: {event: battle_end, subject: self},
effect: [destroy {select: {ref: self}}]} ＋
keywords [blocker, cannot_attack]。このクリーチャーは
攻撃できないためバトルはブロック時（およびタップ
状態で攻撃された時）に限られるが、battle_end は
両参加者を subject として出るため勝敗・攻守を問わず
一致する。

proto T1212（dmrp14-072 型）。判別役は既存 proto を
流用: T001（パワー2000バニラ＝ブロックして勝つ相手）/
T1126（パワー8000ブロッカー＝ブロックして負ける相手）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の
作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import (  # noqa: E402
    DefError, load_rules, load_tables, parse_card)
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

TRIGGER = {"kind": "trigger",
           "when": {"event": "battle_end", "subject": "self"},
           "effect": [{"op": "destroy", "select": {"ref": "self"}}]}
FORM = [TRIGGER]
PARSED_TRIGGER = {"kind": "trigger",
                  "when": {"event": "battle_end", "subject": "self"},
                  "effect": [{"op": "move", "select": {"ref": "self"},
                              "to": "graveyard", "reason": "destroy"}]}
KEYWORDS = ["blocker", "cannot_attack"]
FULL_TEXT = ("ブロッカー（このクリーチャーをタップして、相手クリーチャーの"
             "攻撃先をこのクリーチャーに変更してもよい）\n"
             "このクリーチャーは攻撃できない。\n"
             "このクリーチャーがバトルする時、バトルの後、破壊する。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1212")
    assert c["name"] == "血誓怪人ザミザニン"
    assert c["types"] == ["creature"] and c["civs"] == ["darkness"]
    assert c["cost"] == 2 and c["power"] == 5000 and c["mana"] == 1
    assert c["races"] == ["デビルマスク"]
    assert c["keywords"] == KEYWORDS
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    # destroy は parse で move（to: graveyard, reason: destroy）に
    # 正規化される
    assert PARSED_TRIGGER in d.abilities
    for tid in ("T001", "T1126"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX431", "name": "血誓怪人ザミザニン",
                    "types": ["creature"], "civs": ["darkness"],
                    "cost": 2, "power": 5000, "mana": 1,
                    "races": ["デビルマスク"],
                    "keywords": list(KEYWORDS),
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert PARSED_TRIGGER in d.abilities


def _bad(mutate):
    c = {"id": "TX431B", "name": "x", "types": ["creature"],
         "civs": ["darkness"], "cost": 2, "power": 5000, "mana": 1,
         "abilities": copy.deepcopy(FORM)}
    mutate(c["abilities"][0])
    with pytest.raises(DefError):
        parse_card(c, TABLES)


def test_bad_forms_rejected():
    # when の未知イベントは DefError
    _bad(lambda a: a.update(
        {"when": {"event": "battle_ended", "subject": "self"}}))
    # effect の未知 op は DefError
    _bad(lambda a: a.update(
        {"effect": [{"op": "destroyy", "select": {"ref": "self"}}]}))
    # 未知のキーワードは DefError
    c = {"id": "TX431C", "name": "x", "types": ["creature"],
         "civs": ["darkness"], "cost": 2, "power": 5000, "mana": 1,
         "keywords": ["blocker", "cannot_attackk"],
         "abilities": copy.deepcopy(FORM)}
    with pytest.raises(DefError):
        parse_card(c, TABLES)


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


def _drive_battle(e, attacker_key, block_key, stop, limit=600):
    """相手（p1）の attacker_key を一度だけプレイヤー攻撃
    させ、block_key（自軍ブロッカー）が提示されれば
    ブロックする。stop(e) が真になるまで進める。"""
    st = {"attacked": False, "blocked": False}
    for _ in range(limit):
        if stop():
            return st
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if not st["attacked"] and d["kind"] == "attack" \
                and attacker_key in keys:
            e.answer([keys.index(attacker_key)])
            st["attacked"] = True
            continue
        if d["kind"] == "block":
            hit = [i for i, k in enumerate(keys)
                   if k.startswith(f"bz:{block_key}")]
            if hit:
                e.answer([hit[0]])
                st["blocked"] = True
                continue
        _answer_default(e, d)
    return st


def test_block_and_win_destroys_self_after_battle(rules):
    """ブロックしてバトルに勝っても、バトルの後に自分を
    破壊する。攻撃側はバトルで破壊される（破壊がバトルの
    後であることの判別: バトル開始時破壊なら攻撃側は
    生き残る）。シールドは無傷。"""
    e = _build(rules, {"bz": ["T1212"]}, {"bz": ["T001"]})
    src = _cid(e, 0, "T1212")
    atk = _cid(e, 1, "T001")
    st = _drive_battle(
        e, "attack:T001:player", "T1212",
        stop=lambda: e.s.cards[src].zone == "graveyard"
        and e.s.cards[atk].zone == "graveyard")
    assert st["attacked"] and st["blocked"]
    assert e.s.cards[atk].zone == "graveyard"   # パワー2000はバトルで破壊
    assert e.s.cards[src].zone == "graveyard"   # バトルの後に自己破壊
    assert len(e.zlist("shield", 0)) == 5       # ブロックしたので無傷


def test_block_and_lose_stays_graveyard(rules):
    """ブロックしてバトルに負けた場合はその時点で墓地に
    あり、battle_end 誘発の解決で二重の処理や異常は
    起きない。攻撃側は場に残り、シールドは無傷。"""
    e = _build(rules, {"bz": ["T1212"]}, {"bz": ["T1126"]})
    src = _cid(e, 0, "T1212")
    atk = _cid(e, 1, "T1126")
    st = _drive_battle(
        e, "attack:T1126:player", "T1212",
        stop=lambda: e.s.cards[src].zone == "graveyard")
    assert st["attacked"] and st["blocked"]
    assert e.s.cards[src].zone == "graveyard"
    assert e.s.cards[atk].zone == "bz"
    assert len(e.zlist("shield", 0)) == 5
    # 誘発解決後もゲームが正常に進むこと
    for _ in range(30):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        _answer_default(e, d)
    assert e.s.cards[src].zone == "graveyard"


def test_no_battle_no_destroy_and_cannot_attack(rules):
    """バトルしなければ破壊されない。また、この
    クリーチャーは攻撃できない（自分の攻撃ステップに
    攻撃選択肢が提示されない）まま1巡しても場に残る。"""
    e = _build(rules, {"bz": ["T1212"]}, {"bz": []})
    src = _cid(e, 0, "T1212")
    turns = {"n": 0}
    for _ in range(600):
        d = e.advance()
        if d is None:   # 山札切れでゲーム終了（両者とも
            break       # チャージのみの構成のため）
        keys = _keys(d)
        # 攻撃できない: どの決定にも攻撃選択肢は現れない
        assert not any(k.startswith("attack:T1212") for k in keys)
        if d["kind"] == "charge" and d.get("player") == 0:
            turns["n"] += 1   # 自分のターンが回ってきた回数
        _answer_default(e, d)
    assert turns["n"] >= 2   # 自分のターンが2回以上回った
    assert e.s.cards[src].zone == "bz"
