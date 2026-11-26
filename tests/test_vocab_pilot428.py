"""語彙パイロット第428弾: unblockable_only_when_attacking_creatures
（新規語彙・最小）。

センサス（rejects 1,904件を取り直し）: pure 1,756件
（990家族）/ multi 130件 / 空 gaps 18件。pure の大半は
範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4、ほか超次元・サイキック系の複合
gap 20件）。範囲内の pure は 963家族 / 1,184行
（1件 779、2件 154、3件 23、4件 7）。評価済み却下
（第316〜320・355〜427弾）は再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021、
battle_opponent_reference の残り1件 dmr01-049、
untap_restriction の残り2件（dm26rp1-td004 /
dmx15-011、形が異なると判定済み）、does_not_untap
の残り1件 dm25ex2-031、cast_limit_once_per_turn
の multi 2件、summoning_attack_rule の残り1件
dmex07-s01（partial が素）、entered_turn_attack
の残り1件 dmbd11-d05（J・O・E 等が未構築）、
madness の残り1件 dmx26-028（look/reorder 系の
未確立機構）、次点の destroyed_this_turn_condition /
count_cards_drawn_this_turn、後続候補の
distinct_civ_count、将来の新規語彙候補
first_time_tap、専用ステージ送りの
power_threshold_keyword_gain は覆す根拠が無く
再提案しない。

本弾で個別に評価して見送った候補:
infinity_power_attacker（pure 1、dmr09-v02）。
∞パワーアタッカー自体はキーワード
infinite_power_attacker が第272弾で確立済み
（登録済み3件）で語彙は足りているが、partial
構築済みのドロン・ゴー誘発と5ゾーン分の deny
enter_bz 静的効果が「エグザイル・クリーチャー」の
照合に races [アウトレイジMAX] を代理として
使っており、登録先例 dmd11-001 のドロン・ゴーは
types [exile_creature] で照合する。代理の同値性
（プール全体で同値か）と deny の自己除外の実測が
前提になり検証面が大きい。有力な後続候補として
残す。turn_history_noncreature_played_count
（pure 1、dm25rp4-029）: turn_count は filter
対応済みで部品はあるが、「クリーチャーではない
カードを実行」の範囲が公式の「実行」の定義と
一致するかの確認が未了で、G・ゼロの可否を決める
条件だけに未検証のまま組まない。その他、
battle_win_cost_reference_mana /
graveyard_entered_attack_player（ハイパー機構の
複合）、tap_by_opponent_trigger（tap イベントに
by が記録されない。記録器側の変更が要る）、
other_opponent_shield_break（複数対戦の概念）、
battle_power_external_count（現実世界の数値）、
w_shield_plus / attack_target_power_filter /
untap_by_tapping_mana /
cast_from_both_graveyards_total /
force_attack_target / conditional_require_attack
は docs の選定記録どおり見送った。

範囲内・最小の **unblockable_only_when_attacking_
creatures（pure 2件、multi にも現れない）** を
選定した。対象2件は同一文面「このクリーチャーは、
クリーチャーを攻撃するときブロックされない。／
パワーアタッカー+3000」。行の注記「be_blocked の
deny は攻撃対象で切り替えられない」は実測で
正しい: キーワード unblockable は static
{affects: self, mod: {deny: [be_blocked]}} に
展開され、combat.py phase 2 のブロック候補は
permits（攻撃者, "be_blocked", 候補ブロッカー）
で絞られるが、permits の other はブロッカー
候補側であり攻撃先は参照できない。一方 phase 2
は t["target"] を保持する。第426弾
must_be_blocked と同型の最小追加: mod キー
unblockable_vs_creatures（true のみ）を1つ足し、
攻撃側の特性として集約、phase 2 で「攻撃先が
クリーチャー（"player" でない）かつ攻撃者が
この特性を持つ時、ブロック候補を空にする」。
ガードマンはブロックではない（507.2b）ので
候補に残す（キーワード unblockable が permits
経由でブロッカーだけを消す現行の効き方と一致）。
新しい状態フィールドは無い（Rust state.rs
ミラー不要）。Rust engine.rs には特性のデフォルト
形（unblockable_vs_creatures: false）だけを
同値追加した。集約と消費は Python のみで、
must_be_blocked / require と同じ既存の乖離。
rust_stamp は先例どおり据え置き（この環境に
cargo 無し）。

対象は dm09-030 ジョー・リザード（火 / コスト6 /
パワー3000 / 種族 デューンゲッコー）と dm09-050
鳥神兵クウザ（火 / コスト3 / パワー1000 / 種族
アーマロイド）。両件とも partial は骨格完備で
text は公式全文（公式データ行 by_product/
9.jsonl と一致。**補完なし**）。alias は両件とも
無し（identity 実測で canon_id は対象自身、
aliases_for = []）。第428弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml /
real_zone.yaml / proto.yaml / converted.yaml の
いずれにも登録なし。登録ブロッカーの確認
（第375弾の教訓）: rule_convert.split（両行）は
([], 条項テキスト, [power_when の static]) を
返し、定型所有は第2条項の power_when static
のみ。結論は新規語彙（最小）: abilities 2件
（文面の条項順）:
- 第1条項: static {affects: self, mod:
  {unblockable_vs_creatures: true}}（新規語彙）。
- 第2条項: static {affects: self, mod:
  {power_when: {amount: 3000, when: attacking}}}
  （登録済み dm01-s08 等の確立形で split の
  定型所有形そのもの。partial 内の attack 誘発→
  modify 形は取込時の近似なので使わない）。

proto T1206（dm09-030 型）/ T1207（dm09-050 型）。
判別役は既存 proto を流用: T001（対照の通常
クリーチャー／攻撃先）/ T004（パワー3000
ブロッカー）/ T1126（パワー8000ブロッカー）/
T1205（特性を持たない攻撃者の対照）。

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

STATIC_UB = {"kind": "static", "affects": "self",
             "mod": {"unblockable_vs_creatures": True}}
STATIC_PW = {"kind": "static", "affects": "self",
             "mod": {"power_when": {"amount": 3000,
                                    "when": "attacking"}}}
FORM = [STATIC_UB, STATIC_PW]
FULL_TEXT = ("このクリーチャーは、クリーチャーを攻撃するとき"
             "ブロックされない。\n"
             "パワーアタッカー+3000(攻撃中、このクリーチャーの"
             "パワーは+3000される)")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1206")
    assert c["name"] == "ジョー・リザード"
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 6 and c["power"] == 3000 and c["mana"] == 1
    assert c["races"] == ["デューンゲッコー"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    for a in FORM:
        assert a in d.abilities
    c2 = proto_card("T1207")
    assert c2["name"] == "鳥神兵クウザ"
    assert c2["types"] == ["creature"] and c2["civs"] == ["fire"]
    assert c2["cost"] == 3 and c2["power"] == 1000 and c2["mana"] == 1
    assert c2["races"] == ["アーマロイド"]
    assert c2["text"] == FULL_TEXT
    assert c2["abilities"] == FORM
    d2 = parse_card(copy.deepcopy(c2), TABLES)
    for a in FORM:
        assert a in d2.abilities
    for tid in ("T001", "T004", "T1126", "T1205"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    for tid, cost, power, races in (
            ("TX428A", 6, 3000, ["デューンゲッコー"]),
            ("TX428B", 3, 1000, ["アーマロイド"])):
        d = parse_card({"id": tid, "name": "x",
                        "types": ["creature"], "civs": ["fire"],
                        "cost": cost, "power": power, "mana": 1,
                        "races": races,
                        "abilities": copy.deepcopy(FORM)}, TABLES)
        for a in FORM:
            assert a in d.abilities
        assert len(d.abilities) == 2


def _bad(mod):
    with pytest.raises(DefError):
        parse_card({"id": "TX428B", "name": "x", "types": ["creature"],
                    "civs": ["fire"], "cost": 3, "power": 1000,
                    "abilities": [{"kind": "static", "affects": "self",
                                   "mod": mod}]}, TABLES)


def test_bad_unblockable_vs_creatures_values():
    _bad({"unblockable_vs_creatures": False})
    _bad({"unblockable_vs_creatures": {}})
    _bad({"unblockable_vs_creatures": "yes"})


def test_bad_unknown_mod_key():
    _bad({"bogus_mod": True})


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


def _drive(e, attack_key=None, blocker=None, stop=None, limit=600):
    """attack_key を一度だけ攻撃させ、block 決定が出たら
    blocker（proto id）が選択肢にあればそれを選び、
    無ければ no_block を選ぶ。現れた block 決定の
    options 一覧を log に残す。"""
    st = {"attacked": False}
    log = []
    for _ in range(limit):
        if stop and stop():
            return st, log
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if attack_key and not st["attacked"] and d["kind"] == "attack" \
                and attack_key in keys:
            e.answer([keys.index(attack_key)])
            st["attacked"] = True
            continue
        if d["kind"] == "block":
            log.append(list(keys))
            if blocker:
                hit = [i for i, k in enumerate(keys)
                       if k.startswith(f"bz:{blocker}")]
                if hit:
                    e.answer([hit[0]])
                    continue
            e.answer([keys.index("no_block")])
            continue
        _answer_default(e, d)
    return st, log


def test_characteristic(rules):
    """特性判別: 対象は unblockable_vs_creatures が
    true で、素のパワーは印刷どおり。通常の
    クリーチャーは false。"""
    e = _build(rules, {"bz": ["T1206", "T001"]}, {"bz": []})
    src = _cid(e, 0, "T1206")
    ctl = _cid(e, 0, "T001")
    assert e.chars_ro(src)["unblockable_vs_creatures"] is True
    assert e.chars_ro(src)["power"] == 3000
    assert e.chars_ro(ctl)["unblockable_vs_creatures"] is False


def test_attack_creature_cannot_be_blocked(rules):
    """判別: クリーチャーを攻撃する時はブロック
    できない。相手にアンタップのブロッカー
    （T004）がいても block 決定にブロッカー
    選択肢が現れず、攻撃先（タップした T001、
    パワー2000）はバトルで破壊される（攻撃中
    パワーは 3000+3000=6000）。"""
    e = _build(rules, {"bz": ["T1206"]}, {"bz": ["T001", "T004"]})
    src = _cid(e, 0, "T1206")
    tgt = _cid(e, 1, "T001")
    blk = _cid(e, 1, "T004")
    e.s.cards[tgt].tapped = True
    st, log = _drive(e, attack_key="attack:T1206:T001",
                     stop=lambda: e.s.cards[tgt].zone == "graveyard")
    assert st["attacked"]
    assert all(not any(k.startswith("bz:") for k in ks) for ks in log)
    assert e.s.cards[tgt].zone == "graveyard"
    assert e.s.cards[src].zone == "bz"
    assert e.s.cards[blk].zone == "bz"
    assert not e.s.cards[blk].tapped


def test_attack_player_can_be_blocked(rules):
    """判別: プレイヤーを攻撃する時は通常どおり
    ブロックできる。強いブロッカー（T1126、
    パワー8000）にブロックされると攻撃側
    （攻撃中パワー6000）は破壊され、シールドは
    減らない。"""
    e = _build(rules, {"bz": ["T1206"]}, {"bz": ["T1126"]})
    src = _cid(e, 0, "T1206")
    st, log = _drive(e, attack_key="attack:T1206:player",
                     blocker="T1126",
                     stop=lambda: e.s.cards[src].zone == "graveyard")
    assert st["attacked"]
    assert any(any(k.startswith("bz:T1126") for k in ks) for ks in log)
    assert e.s.cards[src].zone == "graveyard"
    assert len(e.zlist("shield", 1)) == 5


def test_attack_player_unblocked_breaks_one(rules):
    """プレイヤー攻撃をブロックしなければ
    シールドが1枚ブレイクする（ブレイカー系の
    キーワードは持たない）。"""
    e = _build(rules, {"bz": ["T1206"]}, {"bz": ["T004"]})
    src = _cid(e, 0, "T1206")
    st, log = _drive(e, attack_key="attack:T1206:player",
                     stop=lambda: len(e.zlist("shield", 1)) == 4)
    assert st["attacked"]
    assert any(any(k.startswith("bz:T004") for k in ks) for ks in log)
    assert len(e.zlist("shield", 1)) == 4
    assert e.s.cards[src].zone == "bz"


def test_control_attacker_blocked_vs_creature(rules):
    """対照: 特性を持たない攻撃者（T1205）が
    クリーチャーを攻撃する時はブロック決定が
    出て、ブロッカー（T1126）にブロックされると
    攻撃側が破壊され攻撃先は無事。"""
    e = _build(rules, {"bz": ["T1205"]}, {"bz": ["T001", "T1126"]})
    src = _cid(e, 0, "T1205")
    tgt = _cid(e, 1, "T001")
    e.s.cards[tgt].tapped = True
    st, log = _drive(e, attack_key="attack:T1205:T001",
                     blocker="T1126",
                     stop=lambda: e.s.cards[src].zone == "graveyard")
    assert st["attacked"]
    assert any(any(k.startswith("bz:T1126") for k in ks) for ks in log)
    assert e.s.cards[src].zone == "graveyard"
    assert e.s.cards[tgt].zone == "bz"


def test_t1207_attack_creature_cannot_be_blocked(rules):
    """T1207（パワー1000）も同形: クリーチャー
    攻撃はブロックされず、攻撃中パワー
    1000+3000=4000 で T001（2000）を破壊する。"""
    e = _build(rules, {"bz": ["T1207"]}, {"bz": ["T001", "T004"]})
    src = _cid(e, 0, "T1207")
    tgt = _cid(e, 1, "T001")
    e.s.cards[tgt].tapped = True
    st, log = _drive(e, attack_key="attack:T1207:T001",
                     stop=lambda: e.s.cards[tgt].zone == "graveyard")
    assert st["attacked"]
    assert all(not any(k.startswith("bz:") for k in ks) for ks in log)
    assert e.s.cards[tgt].zone == "graveyard"
    assert e.s.cards[src].zone == "bz"


def test_t1207_attack_player_blocked_battle(rules):
    """判別: T1207 のプレイヤー攻撃はブロック
    でき、ブロックした T004（パワー3000）は
    攻撃中パワー4000 に負けて破壊される
    （power_when +3000 がバトルで効くことと、
    プレイヤー攻撃ではブロック可能なことの
    同時判別）。シールドは減らない。"""
    e = _build(rules, {"bz": ["T1207"]}, {"bz": ["T004"]})
    src = _cid(e, 0, "T1207")
    blk = _cid(e, 1, "T004")
    st, log = _drive(e, attack_key="attack:T1207:player",
                     blocker="T004",
                     stop=lambda: e.s.cards[blk].zone == "graveyard")
    assert st["attacked"]
    assert any(any(k.startswith("bz:T004") for k in ks) for ks in log)
    assert e.s.cards[blk].zone == "graveyard"
    assert e.s.cards[src].zone == "bz"
    assert len(e.zlist("shield", 1)) == 5
