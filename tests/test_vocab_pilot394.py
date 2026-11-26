"""語彙パイロット第394弾: only_creature_condition（ドリフト）。

センサス（rejects 1,939件を取り直し）: pure 1,791件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜393弾）は再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021 と
battle_opponent_reference の残り1件 dmr01-049 は
先行弾の評価を覆す根拠が無く再提案しない。
destroyed_this_turn_condition（pure 1、dm26ex2-mc012）は
第393弾の評価どおり依然として最小ではなく次点に残す。
本弾で個別に評価して見送った候補（いずれも docs
未言及で本弾が初評価）: attack_flash_summon
（pure 2。dmx12a-s01 は相手の攻撃宣言時に手札から
出す反応窓が未検証、dmx22a-015 は条件つき出場＋
バトル身代わり＋バトル中パワー修整の複合で均一で
ない）、victory_trait（pure 2。ビクトリーという特性は
公式データにも変換データにもフィールドとして存在せず
テキスト内表記のみで、フィルタで参照できない）、
s_trigger_restriction（pure 1、dmex08-036。単一条項
だが「このクリーチャーがタップしている時」という
自己のタップ状態を static の if で参照する確立形が
無く、第385弾の conditional_tapped_state 却下と同根）、
civ_count_of_destroyed（pure 1、dmex15-b099。
civ_count はセレクタ式で、破壊済みカードへの ref
解決と組み合わせた実挙動が未検証。次点として残す）、
double_freeze（pure 1、dm37-019。フリーズ＝タップ＋
次の相手ターンのはじめにアンタップしない、を表す
op / mod 自体が defs に無い）、tamaseed_from_mana
（pure 2。dmrp21-023 は「自分のマナゾーンから
タマシードを使う」許可の確立形が未確認で、
dm25ex3-rp4s07 は G-NEO 進化等が同居し均一でない）、
discard_replacement_entry（pure 2。手札から捨て
られる時の置換照合は第379・385弾で却下された
madness と同根の未実装照合が要る）、
category_selection / opponent_selects_shield /
play_reaction / compare_card_cost_to_count
（いずれも pure 2 で複合条項・新機構が残る）。
範囲内・未評価で最小の **only_creature_condition
（pure 1件、multi にも現れない）** を選定した。

対象は pure 1件すべて: dm26rp3-056 龍装者 クシュトル
（光 / コスト3 / パワー2500 / 種族 ドラゴンギルド・
メタリカ、mana 1、keywords [blocker]）。公式テキストは
「ブロッカー」のキーワード1件と単一条項:
「自分のクリーチャーがこのクリーチャーだけなら、
このクリーチャーは離れない。」

結論は完全なドリフト（新規語彙・エンジン・defs・
スキーマ変更なし）:

- 「バトルゾーンを離れない」は mod **no_leave**
  （第49弾）。true は無条件で、破壊・バウンスを含む
  あらゆる離脱を止める（判定は events の移動適用時）。
- 条件の門番は登録先例 **dmx22b-040** の形そのまま:
  「自分のシールドが５つ以上なら、自分の光の
  クリーチャーはバトルゾーンを離れない」を
  static {affects: セレクタ, if: {cmp: [{count:
  {zone: shield, owner: you}}, ">=", 5]},
  mod: {no_leave: true}} で登録済み。本弾は
  affects: self（第390・393弾の self static＋if の
  確立形）にし、count を自分のバトルゾーンの
  クリーチャー数（自身を含む）にして == 1 で門番する。
  自分のクリーチャーがこのクリーチャーだけの時、
  count はちょうど1になる。相手のクリーチャーは
  owner: you の数えに入らない。
- no_leave / count / cmp は defs の検証と schema.py
  （生成済み card.schema.json に no_leave 収載）の
  両側に定義済みであることを第408ラウンドの教訓
  どおり確認済み。スキーマ再生成不要・Rust ミラー
  不要・rust_stamp への影響なし。

確立形: **abilities = [static {affects: self, if:
{cmp: [{count: {zone: bz, owner: you, filter:
{types: [creature]}}}, "==", 1]}, mod:
{no_leave: true}}] の1件、keywords = [blocker]**。

partial は骨格完備（keywords [blocker]、abilities
無し）で、text は行の公式テキスト全文と一致する
（**補完なし**）。alias は無い（identity 実測で
canon_id(dm26rp3-056) = dm26rp3-056、aliases_for
は []）。単面カードで未検証の面は無い。登録
ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['blocker'], 条項テキスト, []) を
返し、part[2] の定型所有は空＝ブロッカー無し
（本弾で実測）。第394弾時点で対象 id は real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも登録なしを
確認済み。

proto T1161（dm26rp3-056 型）。判別役は既存 proto を
流用: T1157（火・パワー2000バニラ＝味方役／相手役）/
T056（相手のクリーチャーを破壊する呪文）/ T140
（相手のクリーチャーを持ち主の手札に戻す呪文）/
マナ役 T008（闇）・T009（水）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の作法）。
バトルゾーンは共有ゾーンなので所有は zlist(zone, p) で見る。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

STATIC = {"kind": "static", "affects": "self",
          "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                                    "filter": {"types": ["creature"]}}},
                         "==", 1]},
          "mod": {"no_leave": True}}
FORM = [STATIC]
FULL_TEXT = ("ブロッカー（このクリーチャーをタップして、相手クリーチャーの"
             "攻撃先をこのクリーチャーに変更してもよい）\n"
             "自分のクリーチャーがこのクリーチャーだけなら、"
             "このクリーチャーは離れない。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1161")
    assert c["name"] == "龍装者 クシュトル"
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 3 and c["power"] == 2500 and c["mana"] == 1
    assert c["races"] == ["ドラゴンギルド", "メタリカ"]
    assert c["keywords"] == ["blocker"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities      # keywords は static に展開される


def test_bad_forms_rejected(rules):
    # no_leave の辞書値は bool のみ（第49弾の検証）
    bad = copy.deepcopy(proto_card("T1161"))
    bad["abilities"] = [{"kind": "static", "affects": "self",
                         "mod": {"no_leave": {"except_destroy": "yes"}}}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # 未知の mod キーは DefError
    bad2 = copy.deepcopy(proto_card("T1161"))
    bad2["abilities"] = [{"kind": "static", "affects": "self",
                          "mod": {"no_leave_typo": True}}]
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)
    # cmp の未知の演算子は DefError
    bad3 = copy.deepcopy(proto_card("T1161"))
    bad3["abilities"] = [{"kind": "static", "affects": "self",
                          "if": {"cmp": [{"count": {"zone": "bz",
                                                    "owner": "you"}},
                                          "===", 1]},
                          "mod": {"no_leave": True}}]
    with pytest.raises(DefError):
        parse_card(bad3, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _cid(e, player, defn):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn)


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "yes_no":
        e.answer([keys.index("yes")] if "yes" in keys
                 else list(range(d["min"])))
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _cast_by_p1(rules, p0, p1, spell, choose_defn):
    """p1 が spell を唱え、choose では choose_defn を選び、
    解決が終わる（p1 のアタックフェイズに入る）まで進める。"""
    e = _build(rules, p0, p1)
    state = {}
    for _ in range(4000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 1 \
                and not state.get("cast"):
            assert f"play:{spell}" in keys, keys
            state["cast"] = True
            e.answer([keys.index(f"play:{spell}")])
            continue
        if state.get("cast") and d["kind"] == "choose_cards" \
                and not state.get("chose"):
            idx = [i for i, o in enumerate(d["options"])
                   if choose_defn in o["key"]]
            assert idx, f"{choose_defn} が選択肢に無い: {keys}"
            state["chose"] = True
            e.answer([idx[0]])
            continue
        if state.get("cast") and d["kind"] in ("attack", "charge"):
            break   # メインフェイズは終わり解決済み
        _answer_default(e, d)
    assert state.get("cast"), state
    return e


def test_protected_when_alone(rules):
    # 自分のクリーチャーがこのクリーチャーだけなら
    # no_leave が集約される
    e = _build(rules, {"bz": ["T1161"]}, {"bz": []})
    cid = _cid(e, 0, "T1161")
    assert e.chars(cid)["no_leave"]


def test_not_protected_with_ally(rules):
    # 味方がもう1体いれば count は2で門番が外れる
    e = _build(rules, {"bz": ["T1161", "T1157"]}, {"bz": []})
    cid = _cid(e, 0, "T1161")
    assert not e.chars(cid)["no_leave"]


def test_opponent_creature_does_not_count(rules):
    # owner: you の判別: 相手のクリーチャーは数えない
    e = _build(rules, {"bz": ["T1161"]}, {"bz": ["T1157"]})
    cid = _cid(e, 0, "T1161")
    assert e.chars(cid)["no_leave"]


def test_protection_turns_on_when_ally_leaves(rules):
    # 味方が離れると単独になり、その時点で保護が入る
    e = _build(rules, {"bz": ["T1161", "T1157"]}, {"bz": []})
    cid = _cid(e, 0, "T1161")
    ally = _cid(e, 0, "T1157")
    assert not e.chars(cid)["no_leave"]
    e._raw_move(ally, "graveyard")
    assert e.chars(cid)["no_leave"]


def test_destroy_blocked_when_alone(rules):
    # 実フロー: 単独の間は相手の破壊呪文でも離れない
    e = _cast_by_p1(rules, {"bz": ["T1161"]},
                    {"hand": ["T056"], "mana": ["T008"] * 3},
                    "T056", "T1161")
    cid = _cid(e, 0, "T1161")
    assert e.s.cards[cid].zone == "bz"
    assert not any(e.s.cards[c].defn == "T1161"
                   for c in e.zlist("graveyard", 0))


def test_bounce_blocked_when_alone(rules):
    # 実フロー: 単独の間は相手のバウンス呪文でも
    # 手札に戻らない（no_leave: true は無条件）
    e = _cast_by_p1(rules, {"bz": ["T1161"]},
                    {"hand": ["T140"], "mana": ["T009"] * 3},
                    "T140", "T1161")
    cid = _cid(e, 0, "T1161")
    assert e.s.cards[cid].zone == "bz"
    assert not any(e.s.cards[c].defn == "T1161"
                   for c in e.zlist("hand", 0))


def test_destroy_works_with_ally(rules):
    # 実フロー: 味方がいれば門番が外れ、破壊は通る
    e = _cast_by_p1(rules, {"bz": ["T1161", "T1157"]},
                    {"hand": ["T056"], "mana": ["T008"] * 3},
                    "T056", "T1161")
    assert any(e.s.cards[c].defn == "T1161"
               for c in e.zlist("graveyard", 0))
    assert any(e.s.cards[c].defn == "T1157"
               for c in e.zlist("bz", 0))
