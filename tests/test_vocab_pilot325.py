"""語彙パイロット第325弾: 「シールドをひとつ少なくブレイクする」
（breaks_reduction）— ドリフト（追加語彙なし。エンジン変更なし）。

センサス（rejects 2,045件を取り直し）: pure 1,896件 / multi 131件 /
空 gaps 18件（全て第312〜315弾の監査で別ブロッカー確認済み。
数え方は全行を pure/multi/空に分け、out_of_scope 行も gaps に
従って数える）。pure の大半は範囲外（gr_summon 147、aura 108＝
未承認、hyperdimensional_zone 105、dragheart 45、psychic_filter 45、
hyperdimensional_summon 41、out_of_game 23、duelist_link 20、
outside_game 12＝2026-11-06 ユーザー指示で対象外化済み、
pandora_shift 4）か評価済み DEEP/重い/延期（第318〜324弾の記録参照）。
delayed_return / draw_up_to / look_reorder / flying / does_not_untap
は新しい証拠がない限り再提案しない（第320・321弾で却下済み）。
4件組はすべて評価済み。2件組のうち、after_battle_trigger /
attack_limit_once_per_turn / cip_trigger_double /
s_trigger_suppression / enters_tapped_optional / from_hand_trigger
は第323弾で却下済み。範囲内・未評価で最小の **breaks_reduction
（純粋2件、multi-gap 行にも現れない）** を選定した。

対象は dmr21-007 九極の精霊 マウリエル（光/水・コスト9・パワー12500・
エンジェル・コマンド/革命軍/侵略者・マナ1）/ dm23rp1-004 終納
カボード＝ロウ（闇・コスト8・パワー12000・アビスロイヤル・マナ1）。
両行とも partial あり。by_product で原文照合済み。
- dmr21-007: 「マナゾーンに置く時、このカードはタップして置く。
  ブロッカーT・ブレイカー相手のクリーチャーはすべて、シールドを
  ひとつ少なくブレイクする。」partial は骨格のみ（text は
  「ひとつ少なくブレイクする」だけ）。ブロッカー / T・ブレイカー
  は keywords、常在型が breaks_reduction の1節だけ。
- dm23rp1-004: アビスラッシュ＋T・ブレイカー＋「相手のタップしている
  クリーチャーはすべて、パワーを-5000され、シールドを１つ少なく
  ブレイクする。（パワー０以下のクリーチャーは破壊される）」＋
  「自分の他のアビスすべてのパワーは+5000され、「パワード・
  ブレイカー」を得る」。partial は keywords [triple_breaker,
  abyss_rush]＋アビスの常在型まであり、unsupported はタップ条件の
  常在型ごと1件。注記に「breaks は最大値で集約される」とあるが、
  それは breaks（絶対値）の話で、breaks_add（相対値）は別経路。

結論: ドリフト（追加語彙なし）。breaks_add は負値を取れ、max 合成の
後に既定1を含む使う能力の値すべてへ加算され、0 未満にはならない
（core.py:976-981。:901 の注記も「N枚少なくブレイクする」を
明示している）。形は常在型の mod に breaks_add: -1 を置くだけ:
- 形A（dmr21-007）: {kind: static,
  affects: {owner: opp, filter: {types: [creature]}},
  mod: {breaks_add: -1}}
- 形B（dm23rp1-004）: {kind: static,
  affects: {owner: opp, filter: {types: [creature], tapped: true}},
  mod: {power: -5000, breaks_add: -1}}
（tapped は FILTER_KEYS にある既存のフィルタ。アビスの常在型は
partial どおり既存形。アビスラッシュは keywords abyss_rush で
converted.yaml に先例あり。攻撃するクリーチャーは攻撃の宣言で
タップされるため、攻撃中は tapped: true の対象になる。
そのため形Bのブレイク減少は、相手のクリーチャーの攻撃すべてに
及ぶ）。

注意（既存の扱い）: 「マナゾーンに置く時、このカードはタップして
置く」はデータモデルに無く、text のみで再現する。converted.yaml
に同じ文言の登録カードが359枚あり、いずれも対応する ability /
keyword / フィールドが無い（dm10-037 / dm10-041 等）。
エンジンもマナ配置時のタップは相手の opp_mana_tapped キーワード
持ちにだけ行う。よって dmr21-007 の提出形にもこの節のモデルは
含めない。

プロト T992（dmr21-007 型）/ T993（dm23rp1-004 型）。
次の空きは T994。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card
from tests._conv_cache import proto_card

TABLES = load_tables()

FORM_A = {"kind": "static",
          "affects": {"owner": "opp", "filter": {"types": ["creature"]}},
          "mod": {"breaks_add": -1}}
FORM_B = {"kind": "static",
          "affects": {"owner": "opp",
                      "filter": {"types": ["creature"], "tapped": True}},
          "mod": {"power": -5000, "breaks_add": -1}}
FORM_B2 = {"kind": "static",
           "affects": {"owner": "you", "other": True,
                       "filter": {"race_has": "アビス"}},
           "mod": {"power": 5000, "grant": ["powered_breaker"]}}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_parse_and_forms():
    c992 = proto_card("T992")
    assert c992["abilities"] == [FORM_A]
    assert c992["keywords"] == ["blocker", "triple_breaker"]
    d = parse_card(c992, TABLES)
    assert FORM_A in d.abilities
    c993 = proto_card("T993")
    assert c993["abilities"] == [FORM_B, FORM_B2]
    assert c993["keywords"] == ["triple_breaker", "abyss_rush"]
    d = parse_card(c993, TABLES)
    assert FORM_B in d.abilities and FORM_B2 in d.abilities


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _attack_player(e, attacker_defn, player=0):
    for _ in range(120):
        d = e.advance()
        assert d is not None, "game ended before attack"
        if d["kind"] == "attack" and d.get("player") == player:
            keys = _keys(d)
            e.answer([keys.index(f"attack:{attacker_defn}:player")])
            return
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys
                 else list(range(d["min"])))
    raise AssertionError("attack decision did not appear")


def _drive_combat(e, max_steps=200):
    for _ in range(max_steps):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            return
        keys = _keys(d)
        if d["kind"] == "block":
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("combat did not settle")


def test_opponent_single_breaker_breaks_zero(rules):
    """形A: 相手の単体ブレイカーはシールドを割らない（1-1=0）。
    対照: マウリエル自身（T・ブレイカー）は自分の常在型の対象外
    （相手のクリーチャーだけ）なので3枚割る。"""
    e = setup(rules, {"bz": ["T992"]}, {"bz": ["T001"]})
    e.s.cards[_bz(e, 0, "T992")].entered_turn = -1
    e.s.cards[_bz(e, 1, "T001")].entered_turn = -1
    before = len(e.zlist("shield", 0))
    _attack_player(e, "T001", player=1)
    _drive_combat(e)
    assert len(e.zlist("shield", 0)) == before
    before = len(e.zlist("shield", 1))
    _attack_player(e, "T992")
    _drive_combat(e)
    assert len(e.zlist("shield", 1)) == before - 3


def test_tapped_creature_loses_power(rules):
    """形B: 相手のタップしているクリーチャーはパワー-5000。
    アンタップしている同じクリーチャーには効かない。"""
    e = setup(rules, {"bz": ["T993"]}, {"bz": ["T142", "T142"]})
    t142s = [c for c in e.bz_tops(1)
             if e.s.cards[c].defn == "T142"]
    assert len(t142s) == 2
    e.s.cards[t142s[0]].tapped = True
    assert e.chars(t142s[0])["power"] == 8000
    assert e.chars(t142s[1])["power"] == 13000


def test_attacking_creature_breaks_one_less(rules):
    """形B: 相手のクリーチャーが攻撃する時、攻撃の宣言でタップ
    されるため攻撃中は tapped: true の対象になり、1枚少なく
    ブレイクする（単体ブレイカーなら0枚）。対照: カボード＝ロウが
    いなければ1枚割る。"""
    e = setup(rules, {"bz": ["T993"]}, {"bz": ["T142"]})
    e.s.cards[_bz(e, 1, "T142")].entered_turn = -1
    before = len(e.zlist("shield", 0))
    _attack_player(e, "T142", player=1)
    _drive_combat(e)
    assert len(e.zlist("shield", 0)) == before
    e = setup(rules, {}, {"bz": ["T142"]})
    e.s.cards[_bz(e, 1, "T142")].entered_turn = -1
    before = len(e.zlist("shield", 0))
    _attack_player(e, "T142", player=1)
    _drive_combat(e)
    assert len(e.zlist("shield", 0)) == before - 1
