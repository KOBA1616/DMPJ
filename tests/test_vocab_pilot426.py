"""語彙パイロット第426弾: must_be_blocked（新規語彙・最小）。

センサス（rejects 1,906件を取り直し）: pure 1,758件
（992家族）/ multi 130件 / 空 gaps 18件。pure の大半は
範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。範囲内の pure は 982家族 / 1,208行
（1件家族 793、2件 159、3件 23、4件 7）。
評価済み却下（第316〜320・355〜425弾）は再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021、
battle_opponent_reference の残り1件 dmr01-049、
untap_restriction の残り2件（dm26rp1-td004 /
dmx15-011、形が異なると判定済み）、does_not_untap の
残り1件（dm25ex2-031、形が異なると判定済み）、
cast_limit_once_per_turn の multi 2件（dm26ex2-pr006 /
dm26ex4-cho031）、summoning_attack_rule の残り1件
dmex07-s01（partial が素）、entered_turn_attack の
残り1件 dmbd11-d05（J・O・E 等が未構築）、madness の
残り1件 dmx26-028（look/reorder 系の未確立機構）は
先行弾の評価を覆す根拠が無く再提案しない。
destroyed_this_turn_condition と count_cards_drawn_
this_turn は次点のまま残す。distinct_civ_count
（3条項の複合）は後続候補のまま。first_time_tap
（pure 2）は将来の新規語彙候補として残置する。

本弾で個別に評価して見送った候補:
power_threshold_keyword_gain（pure 1、dm24-011
彩空の精霊フォルテイン）。第2・第3条項「パワー6000
以上でW・ブレイカー／12000以上でかわりにT・
ブレイカー」の候補形 static {affects: self,
if: {exists: {ref: self, filter: {power_ge: N}}},
mod: {grant: [double_breaker]}} は登録済み
dm10-s01 / dm10-s08 に逐語先例があるが、**実測で
不発**: 対象形を実フローでパワー15000まで上げても
（召喚・詠唱の監視誘発は正常に発火）ブレイク数は
1のまま付与が掛からず、cmp + power_of {ref: self}
形でも同じ。さらに**登録済み dm10-s01 自体**を
4文明マナでパワー13000にして測っても double_
breaker は付与されなかった。自己の現在パワーを
読む static if は特性計算への再入ガードで印刷
パワーを読み、閾値付与は構造的に発火しない
（第396弾の civ_count {ref: self} の教訓と同根。
当該登録カード群は一括取込の review: pending で
ブレイク条項が死んでいる）。正確な表現には特性
評価順のエンジン変更（全静的効果に及ぶ設計判断）
が要るため専用ステージ送りとし、本弾では扱わない。
第1条項（文明つき召喚・詠唱の監視誘発→自己
+5000）は確立形そのものだが、条項2・3が組めない
以上カード単位では登録できない。
mirror_opponent_draw（pure 1、dm23bd7-029）。
draw の履歴記録はカード単位（rec / ord とも
1枚ごと）で、「引いた時」の監視誘発は引いた
枚数だけ発火する。文面は「引いたら、自分も
同じ数引いてもよい」の一括の任意判断であり、
1枚ごとの may 判断に分解すると「一部だけ引く」
選択肢が生まれて文面と一致しない。最小でない。

範囲内・最小の **must_be_blocked（pure 1件、
multi にも現れない）** を選定した。第368弾では
「must_be_attacked は攻撃先の強制でブロックの
強制とは別機構」として見送られたが、それは既存
mod では表せないことの確認であり却下理由では
ない。第410弾の実測で combat.py のブロック宣言
（phase 2）の強制機構（require [block] があれば
no_block 選択肢が消える）は確認済みで、欠けて
いるのはキーになる特性が防御側でなく攻撃側で
ある点だけ。新規語彙は最小限に: mod キー
must_be_blocked（true のみ）を1つ足し、特性
must_be_blocked として集約、phase 2 で「その
攻撃をブロックできるクリーチャーが1体でも
いれば no_block を消す」。must_be_attacked
（第51弾）/ must_attack_creature（第171弾）と
同じ must_* 特性族の追加で、新しい状態
フィールドは無い（Rust state.rs ミラー不要。
test_rust_schema_sync は Card/GameState の
フィールド照合のみ）。Rust engine.rs には
特性のデフォルト形（must_be_blocked: false）
だけを同値追加した。must_be_attacked /
must_attack_creature / require の強制と同様、
集約と消費は Python のみで、Rust 側の強制
実装は既存の乖離のまま触らない。rust_stamp は
先例どおり据え置き（この環境に cargo 無し）。

対象は dmex08-291 薩摩の超人（自然の
クリーチャー / コスト9 / パワー13000 / 種族
ジャイアント/サムライ）。公式テキスト:
「T・ブレイカー／自分のジャイアントはすべて、
可能ならブロックされる。／自分のターン中、
自分のジャイアントがバトルに勝った時、相手の
シールドを１つブレイクする。」partial は骨格
完備（mana 1、keywords [triple_breaker]）で
text は公式全文と一致するため**補完なし**。
未解決は unsupported の must_be_blocked 1件
だけ（第2条項の trigger は partial に構築済み）。
alias は dm31-s03（partial の source.aliases
のみ、自前の reject 行は無い。identity 実測で
canon_id は対象自身、aliases_for = [dm31-s03]、
dm31-s03 の canon も対象）。第426弾時点で
real.yaml / real_akashic.yaml / real_vocab.yaml /
real_zone.yaml / proto.yaml / converted.yaml の
いずれにも対象・別刷りとも登録なし。単面
カードで未検証の面は無い。登録ブロッカーの
確認（第375弾の教訓）: rule_convert.split
（対象行）は (['triple_breaker'], 条項テキスト,
[]) を返し、part[2] の定型所有は**空**
（ツール側ブロッカーなし。提出形には FORM の
能力2件すべてを含めること）。

結論は新規語彙（最小）: mod {must_be_blocked:
true}。確立形は abilities 2件（文面の条項順）:
- 第1条項は static {affects: {zone: bz,
  owner: you, filter: {types: [creature],
  races: [ジャイアント]}}, mod: {must_be_
  blocked: true}}。発生源自身もジャイアント
  なので自分も対象に含まれる（「すべて」）。
- 第2条項は partial 構築済みの trigger
  {when: {event: battle_win, subject:
  {owner: you, filter: {races: [ジャイアント]}}},
  if: {is_turn: you}, effect: [break
  {player: opp, count: 1}]} をそのまま使う。

proto T1204（dmex08-291 型）。判別役は既存
proto を流用: T1044（自分の別のジャイアント役・
相手のジャイアント対照役）/ T001（非ジャイアント
対照）/ T004・T1078・T1085（防御側ブロッカー役）。

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

STATIC = {"kind": "static",
          "affects": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["creature"],
                                 "races": ["ジャイアント"]}},
          "mod": {"must_be_blocked": True}}
TRIGGER = {"kind": "trigger",
           "when": {"event": "battle_win",
                    "subject": {"owner": "you",
                                "filter": {"races": ["ジャイアント"]}}},
           "if": {"is_turn": "you"},
           "effect": [{"op": "break", "player": "opp", "count": 1}]}
FORM = [STATIC, TRIGGER]
FULL_TEXT = ("T・ブレイカー\n"
             "自分のジャイアントはすべて、可能ならブロックされる。\n"
             "自分のターン中、自分のジャイアントがバトルに勝った時、"
             "相手のシールドを１つブレイクする。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1204")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 9 and c["power"] == 13000 and c["mana"] == 1
    assert c["races"] == ["ジャイアント", "サムライ"]
    assert c["keywords"] == ["triple_breaker"]
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    for a in FORM:
        assert a in d.abilities
    for tid in ("T001", "T004", "T1044", "T1078", "T1085"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX426", "name": "薩摩の超人",
                    "types": ["creature"], "civs": ["nature"],
                    "cost": 9, "power": 13000, "mana": 1,
                    "races": ["ジャイアント", "サムライ"],
                    "keywords": ["triple_breaker"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    for a in FORM:
        assert a in d.abilities
    # parse 後の triple_breaker 派生 static を除き2件
    assert len(d.abilities) == 3


def _bad(mod):
    with pytest.raises(DefError):
        parse_card({"id": "TX426B", "name": "x", "types": ["creature"],
                    "civs": ["nature"], "cost": 9, "power": 13000,
                    "abilities": [{"kind": "static", "affects": "self",
                                   "mod": mod}]}, TABLES)


def test_bad_must_be_blocked_values():
    _bad({"must_be_blocked": False})
    _bad({"must_be_blocked": {}})
    _bad({"must_be_blocked": "yes"})


def test_bad_unknown_mod_key():
    _bad({"bogus_mod": True})


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, defn, p, nth=0):
    return [c for c in e.bz_tops(p) if e.cdef(c).id == defn][nth]


def _keys(d):
    return [o["key"] for o in d["options"]]


def _zone_tapped(e, defn):
    for cd in e.s.cards:
        if cd.defn == defn:
            return cd.zone, cd.tapped
    raise AssertionError(defn)


def _attack_until(e, attacker, done, block_answer=None, limit=300):
    """attacker（defn）でプレイヤー攻撃し、done() が真に
    なるまで進める。現れた block 決定の options を返す。"""
    seen = []
    atk = f"attack:{attacker}:player"
    for _ in range(limit):
        if done():
            return seen
        d = e.advance()
        if d is None:
            return seen
        ks = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 and atk in ks:
            e.answer([ks.index(atk)])
        elif d["kind"] == "block":
            seen.append(list(ks))
            if block_answer is not None and block_answer in ks:
                e.answer([ks.index(block_answer)])
            elif "no_block" in ks:
                e.answer([ks.index("no_block")])
            else:
                e.answer([0])
        elif "pass" in ks:
            e.answer([ks.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return seen


def test_chars_discrimination(rules):
    """特性レベルの判別: 自分のジャイアント（発生源自身を
    含む）は must_be_blocked を得る。自分の非ジャイアントと
    相手のジャイアントは得ない。"""
    e = _build(rules,
               {"bz": ["T1204", "T1044", "T001"]},
               {"bz": ["T1044"]})
    assert e.chars(_cid(e, "T1204", 0))["must_be_blocked"] is True
    assert e.chars(_cid(e, "T1044", 0))["must_be_blocked"] is True
    assert e.chars(_cid(e, "T001", 0))["must_be_blocked"] is False
    assert e.chars(_cid(e, "T1044", 1))["must_be_blocked"] is False
    # T・ブレイカーは特性どおり3枚ブレイク
    assert e.chars(_cid(e, "T1204", 0))["breaks"] == 3


def test_forced_block_single_blocker(rules):
    """ブロッカーが1体だけでも強制: 選択肢は一意で決定は
    出ず（ask の一意自動解決）、ブロックが成立する。
    ブロッカーは破壊され、第2条項で相手のシールドが
    1つだけブレイクする（ブロックされたので T・ブレイカーの
    3枚ブレイクにはならない）。"""
    e = _build(rules, {"bz": ["T1204"]}, {"bz": ["T004"]})
    seen = _attack_until(e, "T1204",
                         lambda: len(e.zlist("shield", 1)) == 4)
    assert seen == []
    assert _zone_tapped(e, "T004") == ("graveyard", False)
    assert len(e.zlist("shield", 1)) == 4


def test_no_force_when_blocker_cannot_block(rules):
    """「可能なら」の判別: ブロッカーがタップしていて
    ブロックできない時は強制は働かず、攻撃は通って
    T・ブレイカーで3枚ブレイクする。"""
    e = _build(rules, {"bz": ["T1204"]}, {"bz": ["T004"]})
    e.s.cards[_cid(e, "T004", 1)].tapped = True
    seen = _attack_until(e, "T1204",
                         lambda: len(e.zlist("shield", 1)) == 2)
    assert seen == []
    assert len(e.zlist("shield", 1)) == 2


def test_non_giant_attacker_not_forced(rules):
    """対照: 非ジャイアントの攻撃には強制が掛からず、
    block 決定に no_block が残る。ブロックしなければ
    その攻撃のブレイクだけが起きる。"""
    e = _build(rules, {"bz": ["T1204", "T001"]}, {"bz": ["T004"]})
    seen = _attack_until(e, "T001",
                         lambda: len(e.zlist("shield", 1)) == 4,
                         block_answer="no_block")
    assert seen == [["bz:T004:0", "no_block"]]
    assert _zone_tapped(e, "T004") == ("bz", False)
    assert len(e.zlist("shield", 1)) == 4


def test_two_blockers_defender_chooses(rules):
    """ブロッカーが2体いる時は決定が出るが no_block は
    無い（防御側はどちらでブロックするかだけを選ぶ）。
    タップしてバトルするのは選ばれた1体だけ（第410弾の
    修正との整合）。第2条項のブレイクも1つ起きる。"""
    e = _build(rules, {"bz": ["T1204"]}, {"bz": ["T1078", "T1085"]})
    seen = _attack_until(e, "T1204",
                         lambda: len(e.zlist("shield", 1)) == 4,
                         block_answer="bz:T1078:0")
    assert seen == [["bz:T1078:0", "bz:T1085:0"]]
    assert _zone_tapped(e, "T1078") == ("graveyard", False)
    assert _zone_tapped(e, "T1085") == ("bz", False)
    assert len(e.zlist("shield", 1)) == 4


def test_other_giant_forced_and_tie_no_break(rules):
    """発生源以外の自分のジャイアントの攻撃にも強制が
    掛かる。パワー同値の相打ちではバトルに勝っていない
    ので第2条項のブレイクは起きない。"""
    e = _build(rules, {"bz": ["T1204", "T1044"]}, {"bz": ["T004"]})
    seen = _attack_until(
        e, "T1044",
        lambda: _zone_tapped(e, "T004") != ("bz", False))
    assert seen == []
    assert _zone_tapped(e, "T1044") == ("graveyard", False)
    assert _zone_tapped(e, "T004") == ("graveyard", False)
    assert len(e.zlist("shield", 1)) == 5


def test_no_source_no_force(rules):
    """対照: 発生源がいなければ同じジャイアントの攻撃でも
    強制は無く、no_block が残る。"""
    e = _build(rules, {"bz": ["T1044"]}, {"bz": ["T004"]})
    seen = _attack_until(e, "T1044",
                         lambda: len(e.zlist("shield", 1)) == 4,
                         block_answer="no_block")
    assert seen == [["bz:T004:0", "no_block"]]
    assert _zone_tapped(e, "T004") == ("bz", False)
