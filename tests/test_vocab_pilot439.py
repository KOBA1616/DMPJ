"""語彙パイロット第439弾: untap_prevention（ドリフト）。

センサス（rejects 1,893件を取り直し）: pure 1,745件
（982家族）/ multi 130件 / 空 gaps 18件。pure の大半は
範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜438弾）は原則として再提案しない。残置群
（graveyard_replacement 残り dm25ex2-cho021、
battle_opponent_reference 残り dmr01-049、
untap_restriction 残り2件、does_not_untap 残り
dm25ex2-031、revolution_2 残り dm26sd1-o004、
cast_limit_once_per_turn の multi 2件、
summoning_attack_rule 残り dmex07-s01、
entered_turn_attack 残り dmbd11-d05、madness 残り
dmx26-028、after_battle_trigger 残り dmrp09-074、
s_trigger_suppression 2件＝第435弾で専用ステージ
送り確定、次点の destroyed_this_turn_condition /
count_cards_drawn_this_turn /
player_not_attacked_while_tapped、後続候補の
distinct_civ_count、将来の新規語彙候補 first_time_tap /
turn_history_entry / played_free_condition、専用
ステージ送りの power_threshold_keyword_gain）は
覆す根拠が無く再提案しない。

範囲内・最小の **untap_prevention（pure 1件）の
dmr14-006 のみ** を選定した。本ファミリーは過去2度
見送られた: (1) 第381弾前後は「条件つき全体
アンタップ防止で本弾の最小ではない」という最小性の
判断のみ、(2) 第392弾前後は「常在否定の確立形が
未確認」。本弾の実測で (2) の未確認が解けたため、
その評価を覆して着手する（第435〜437弾と同型）。

対象は dmr14-006 聖霊龍王 スタグネイト（光 /
コスト5 / パワー10500 / 種族 エンジェル・コマンド・
ドラゴン / mana 1）。partial は骨格完備
（evolve_from {civs: [light], race_has: ドラゴン}
を含む）で text は断片（「アンタップされない」）、
keywords・abilities は未構築。**補完あり: text
（公式全文）＋keywords [double_breaker]＋abilities**。
alias は無し（identity 実測で canon は対象自身、
同名の公式行は r14 の1件のみ）。

結論はドリフト（追加語彙・エンジン・defs・スキーマ
変更なし）。条項「このクリーチャーがタップしている時、
バトルゾーンにある相手のクリーチャーは相手のターン
のはじめにアンタップされない」の形は static 1件:

- static {affects: {zone: bz, owner: opp, filter:
  {types: [creature]}}, if: {exists: {ref: self,
  filter: {tapped: true}}}, mod: {deny:
  [untap_at_start]}}

根拠: 条件 if {exists: {ref: self, filter:
{tapped: true}}} は登録済み dmx02-027（「この
クリーチャーがタップされている時、自分の他の
ビーストフォークすべてのパワーは+2000される」）の
static の if そのもの。deny [untap_at_start] の
常在型は第400弾の確立形（登録済み dmrp06-027）で、
affects セレクタへの常在 deny は登録済み dm10-033
（affects {owner: you, zone: mana}）が先例。
エンジンのアンタップステップは permits(c,
"untap_at_start") を見る（第400弾で実測）。
もう一つの候補形 untap_limit {zone: bz, count: 0}
（第227弾、登録済み dmr12-007 / dmx20-001）は
ゾーン単位の上限でタマシード等クリーチャー以外も
巻き込むため、文面（クリーチャー限定）に一致する
deny 形を採る。公式境界: 文面は「相手のターンの
はじめに」限定で、deny untap_at_start は効果による
アンタップを妨げない（登録済み dmrp15-012 等の
先例注記どおり）。

proto T1229（dmr14-006 型）。判別役は T001（相手
クリーチャー役・対照役）/ T189（タマシード＝
クリーチャー限定の範囲判別役）。

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

FORM = [{"kind": "static",
         "affects": {"zone": "bz", "owner": "opp",
                     "filter": {"types": ["creature"]}},
         "if": {"exists": {"ref": "self",
                           "filter": {"tapped": True}}},
         "mod": {"deny": ["untap_at_start"]}}]
FULL_TEXT = ("進化ー自分の光のドラゴン１体の上に置く。"
             "W・ブレイカー（このクリーチャーはシールドを"
             "２枚ブレイクする）"
             "このクリーチャーがタップしている時、"
             "バトルゾーンにある相手のクリーチャーは"
             "相手のターンのはじめにアンタップされない。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1229")
    assert c["name"] == "聖霊龍王 スタグネイト"
    assert c["types"] == ["creature", "evolution"]
    assert c["civs"] == ["light"]
    assert c["cost"] == 5 and c["power"] == 10500
    assert c["races"] == ["エンジェル・コマンド・ドラゴン"]
    assert c["mana"] == 1
    assert c["text"] == FULL_TEXT
    assert c["keywords"] == ["double_breaker"]
    assert c["evolve_from"] == {"civs": ["light"],
                                 "race_has": "ドラゴン"}
    assert c["abilities"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    assert {"kind": "static", "affects": "self",
            "mod": {"breaks": 2},
            "keyword": "double_breaker"} in d.abilities
    assert FORM[0] in d.abilities


def test_form_def_errors():
    base = {"id": "X439", "name": "x",
            "types": ["creature", "evolution"],
            "civs": ["light"], "cost": 5, "power": 10500,
            "races": ["テスト"], "mana": 1, "text": "x",
            "keywords": ["double_breaker"],
            "evolve_from": {"civs": ["light"],
                            "race_has": "ドラゴン"},
            "abilities": copy.deepcopy(FORM)}
    parse_card(copy.deepcopy(base), TABLES)
    # 未知の deny アクション
    bad = copy.deepcopy(base)
    bad["abilities"][0]["mod"] = {"deny": ["untap_at_strt"]}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # if の exists filter の未知キー
    bad = copy.deepcopy(base)
    bad["abilities"][0]["if"]["exists"]["filter"] = \
        {"tappedd": True}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # affects の未知ゾーン
    bad = copy.deepcopy(base)
    bad["abilities"][0]["affects"]["zone"] = "bzz"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # 未知の mod キー
    bad = copy.deepcopy(base)
    bad["abilities"][0]["mod"] = {"denyy": ["untap_at_start"]}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _cid(e, defn, player, zone):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn
                and e.s.cards[c].controller == player)


def test_permits_discrimination(rules):
    """特性判別: 発生源がタップしている間だけ、相手の
    クリーチャーの untap_at_start が deny される。
    攻撃許可・タマシード・自分のクリーチャーは対象外。"""
    e = scenario.build(rules, {
        "p0": {"bz": ["T1229", "T001"]},
        "p1": {"bz": ["T001", "T189"]},
        "filler": "T002", "seed": 1, "deck_size": 20})
    src = _cid(e, "T1229", 0, "bz")
    own = _cid(e, "T001", 0, "bz")
    opp = _cid(e, "T001", 1, "bz")
    seed = _cid(e, "T189", 1, "bz")
    # 発生源がアンタップ状態では deny は付かない
    assert e.permits(opp, "untap_at_start") is True
    e.s.cards[src].tapped = True
    assert e.permits(opp, "untap_at_start") is False
    # deny は untap_at_start だけ（攻撃許可は奪わない）
    assert e.permits(opp, "attack_player") is True
    assert e.permits(opp, "attack_creature") is True
    # クリーチャー限定: タマシードには付かない
    assert e.permits(seed, "untap_at_start") is True
    # 自分のクリーチャーには付かない
    assert e.permits(own, "untap_at_start") is True
    # 発生源自身にも付かない（affects は owner: opp）
    assert e.permits(src, "untap_at_start") is True
    # 発生源がアンタップに戻れば deny は消える
    e.s.cards[src].tapped = False
    assert e.permits(opp, "untap_at_start") is True


def test_permits_no_source(rules):
    """発生源が場に無ければ deny は付かない。"""
    e = scenario.build(rules, {
        "p0": {"bz": ["T001"]},
        "p1": {"bz": ["T001"]},
        "filler": "T002", "seed": 1, "deck_size": 20})
    opp = _cid(e, "T001", 1, "bz")
    assert e.permits(opp, "untap_at_start") is True


def _keys(d):
    return [o.get("key") for o in d["options"]]


def _drive(e, want=None, limit=600):
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if want is not None:
            k = want(d["kind"], keys, d)
            if k is not None:
                e.answer([keys.index(k)])
                continue
        if d["kind"] in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return e


def _flow(rules, source_attacks):
    """共通フロー: 相手の T001 は最初の自ターンに攻撃して
    タップする。発生源 T1229 は source_attacks の時だけ
    自ターンごとに攻撃してタップし直す。相手ターン2の
    charge（アンタップステップ後）での T001 と、
    自分ターン2の charge での T1229 のタップ状態を返す。"""
    e = scenario.build(rules, {
        "p0": {"bz": ["T1229"], "shield": ["T002"] * 5},
        "p1": {"bz": ["T001"], "shield": ["T002"] * 5},
        "filler": "T002", "seed": 1, "deck_size": 20})
    src = _cid(e, "T1229", 0, "bz")
    opp = _cid(e, "T001", 1, "bz")
    st = {"charges": {0: 0, 1: 0}, "opp_attacked": False,
          "opp_at_t2": None, "src_at_t2": None}

    def want(kind, keys, d):
        pl = d.get("player")
        if kind == "charge" and pl in (0, 1):
            st["charges"][pl] += 1
            if pl == 1 and st["charges"][1] == 2 \
                    and st["opp_at_t2"] is None:
                st["opp_at_t2"] = e.s.cards[opp].tapped
            if pl == 0 and st["charges"][0] == 2 \
                    and st["src_at_t2"] is None:
                st["src_at_t2"] = e.s.cards[src].tapped
            return None
        if kind == "attack" and pl == 1 \
                and not st["opp_attacked"] \
                and "attack:T001:player" in keys:
            st["opp_attacked"] = True
            return "attack:T001:player"
        if kind == "attack" and pl == 0 and source_attacks \
                and "attack:T1229:player" in keys:
            return "attack:T1229:player"
        return None

    _drive(e, want, limit=600)
    assert st["opp_attacked"], "相手の T001 が攻撃しなかった"
    assert st["opp_at_t2"] is not None, "相手ターン2に届かなかった"
    assert st["src_at_t2"] is not None, "自分ターン2に届かなかった"
    return st


def test_flow_opponent_stays_tapped_when_source_tapped(rules):
    """発生源がタップしている間、相手のクリーチャーは
    相手のターンのはじめにアンタップしない。発生源自身は
    自分のターンのはじめに通常どおりアンタップする
    （affects は owner: opp の判別）。"""
    st = _flow(rules, source_attacks=True)
    assert st["src_at_t2"] is False  # 自分のはじめに起きた
    assert st["opp_at_t2"] is True   # 相手は起きない


def test_flow_opponent_untaps_when_source_untapped(rules):
    """対照: 発生源がタップしていなければ、相手の
    クリーチャーは通常どおりアンタップする。"""
    st = _flow(rules, source_attacks=False)
    assert st["src_at_t2"] is False
    assert st["opp_at_t2"] is False
