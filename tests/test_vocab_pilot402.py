"""語彙パイロット第402弾: indestructible_duration（ドリフト）。

センサス（rejects 1,931件を取り直し）: pure 1,783件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜401弾）は再提案しない。
graveyard_replacement の残り1件（dm25ex2-cho021）、
battle_opponent_reference の残り1件（dmr01-049）、
untap_restriction の残り2件（dm26rp1-td004 /
dmx15-011）は先行弾の評価を覆す根拠が無く再提案
しない。destroyed_this_turn_condition と
count_cards_drawn_this_turn は次点のまま残す。
enters_tapped_rule（dmex11-005、静的効果3件）は
後続候補のまま。本弾で個別に評価して見送った候補:
battle_indestructible（pure 1、dmd27-012。行に
name・text・partial が一切無い素行で、対象カードの
条項自体を特定できず評価不能）、fixed_breaks_plus_one
（pure 1、dmrp07-052。同様の素行で評価不能）、
power_set（pure 2件、∑龍 dm26rp3-or001 /
dm26rp3-sec001。partial の注記は第370・372弾の
power_set 登録より前の陳腐化だが、カードには
「パワーが0以下の間離れない」＝自分の現在パワーを
条件にする no_leave が同居し、その条件形
（static_if_own_current_power）は未検証の別機構の
ため本 gap 単独では登録形が定まらない）、
no_untap_rule（pure 1、dmex08-207。本 gap の条項
自体は第400弾の形だが、partial に能力が何も構築
されておらず、第4条項「自分のターン、1枚目の
カードを引く時、マナを3枚タップしてもよい。そう
したらアンタップする」の支払い型 may が未検証で
本弾より重い）、static_double_power（pure 1、
dmrp19-008。「バトル中パワーを2倍にする」は
battle_power の乗算形が無く新規語彙が要る）、
destroy_after_battle（pure 1、dm07-003。「この
ターンにバトルしたクリーチャー」の追跡＋バトル後
破壊は未確立）。範囲内・最小の
**indestructible_duration（pure 1件、multi にも
現れない）** を選定した。

対象は promoy13-019 天英雄 ヴァルハラ・デューク
（光のクリーチャー / コスト7 / パワー7000 / 種族
エンジェル・コマンド・ドラゴン）。partial は骨格
完備＋keywords [double_breaker] が構築済みで、
未解決は unsupported の indestructible_duration
1件だけ。partial の text は公式全文と一致するため
**補完なし**。alias は無い（identity 実測で
canon_id は対象自身、aliases_for = []）。条項は
すべて確立済みの部品で表せる（追加語彙なし）:

- 「マナ武装 ７：このクリーチャーをバトルゾーンに
  出した時、自分のマナゾーンに光のカードが７枚
  以上あれば、次の自分のターンのはじめまで自分の
  クリーチャーは破壊されない」は、出た時誘発に
  条件 if {cmp: [{count: {zone: mana, owner: you,
  filter: {civs: [light]}}}, ">=", 7]} を付け
  （マナ武装を誘発の if で表す登録先例の作法）、
  効果を第127弾の indestructible の一括 modify で
  与える: modify {select: {zone: bz, owner: you,
  filter: {types: [creature]}, count: all}, mod:
  {indestructible: true}, duration:
  until_next_own_turn_start}。一括 modify
  （count: all）の確立形は登録済み dm23sd2-013
  （出た時誘発→modify count: all の indestructible、
  duration: end_of_turn）と同型で、duration:
  until_next_own_turn_start と indestructible の
  併用も登録先例がある（dmrp15-030 は select が
  ref の形）。一括 modify は解決時に集合が固定
  される（第372弾の実測どおり非 dynamic）ため、
  解決後にバトルゾーンに出たクリーチャーは対象に
  含まれない（本体テストで固定）。W・ブレイカーは
  keyword double_breaker（partial 構築済み）。
  count / if の cmp / modify / indestructible /
  duration はいずれも既存キーで、defs と
  schema.py の両側に定義済みを確認（第408
  ラウンドの教訓）。登録ブロッカーの確認
  （第375弾の教訓）: rule_convert.split（対象行）
  は (['double_breaker'], 条項テキスト, []) を
  返し、part[2] の定型所有は空＝ブロッカー無し
  （本弾で実測）。

確立形: abilities = [上記 trigger] の1件、
keywords = [double_breaker]。

proto T1169（promoy13-019 型）。判別役は既存
proto を流用: T1117（光マナ役）/ T001（相手役・
非光マナ役）/ T004（ブロッカー味方役）/ T1118
（パワー7000の攻撃役）/ T056（相手の破壊呪文役）/
T620（自分の単体破壊呪文役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED
が復活するので scenario.build を直接包む
（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

TRIGGER = {"kind": "trigger",
           "when": {"event": "move", "to": "bz", "subject": "self"},
           "if": {"cmp": [{"count": {"zone": "mana", "owner": "you",
                                     "filter": {"civs": ["light"]}}},
                          ">=", 7]},
           "effect": [{"op": "modify",
                       "select": {"zone": "bz", "owner": "you",
                                  "filter": {"types": ["creature"]},
                                  "count": "all"},
                       "mod": {"indestructible": True},
                       "duration": "until_next_own_turn_start"}]}
FORM = [TRIGGER]
FULL_TEXT = ("マナ武装 ７：このクリーチャーをバトルゾーンに出した時、"
             "自分のマナゾーンに光のカードが７枚以上あれば、"
             "次の自分のターンのはじめまで自分のクリーチャーは"
             "破壊されない。\n"
             "W・ブレイカー（このクリーチャーはシールドを２枚"
             "ブレイクする）")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1169")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"]
    assert c["civs"] == ["light"] and c["cost"] == 7
    assert c["power"] == 7000 and c["mana"] == 1
    assert c["races"] == ["エンジェル・コマンド・ドラゴン"]
    assert c["keywords"] == ["double_breaker"]
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.abilities == rules.cards["T1169"].abilities
    for tid in ("T1117", "T001", "T004", "T1118", "T056", "T620"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX402", "name": "x",
                    "types": ["creature"], "civs": ["light"],
                    "cost": 7, "power": 7000,
                    "races": ["エンジェル・コマンド・ドラゴン"],
                    "mana": 1, "keywords": ["double_breaker"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    p = parse_card(proto_card("T1169"), TABLES)
    assert d.abilities == p.abilities


def _bad(**over):
    base = {"id": "TX402", "name": "x",
            "types": ["creature"], "civs": ["light"],
            "cost": 7, "power": 7000,
            "races": ["エンジェル・コマンド・ドラゴン"],
            "mana": 1, "keywords": ["double_breaker"],
            "abilities": copy.deepcopy(FORM)}
    base.update(over)
    return base


def test_invalid_forms():
    # indestructible は true でなければならない
    bad = copy.deepcopy(FORM)
    bad[0]["effect"][0]["mod"] = {"indestructible": "yes"}
    with pytest.raises(DefError):
        parse_card(_bad(abilities=bad), TABLES)
    # 未知の duration
    bad = copy.deepcopy(FORM)
    bad[0]["effect"][0]["duration"] = "forever"
    with pytest.raises(DefError):
        parse_card(_bad(abilities=bad), TABLES)
    # if の未知の比較演算子
    bad = copy.deepcopy(FORM)
    bad[0]["if"] = {"cmp": [{"count": {"zone": "mana", "owner": "you",
                                       "filter": {"civs": ["light"]}}},
                            ">>", 7]}
    with pytest.raises(DefError):
        parse_card(_bad(abilities=bad), TABLES)
    # modify の未知キー
    bad = copy.deepcopy(FORM)
    bad[0]["effect"][0]["bogus"] = 1
    with pytest.raises(DefError):
        parse_card(_bad(abilities=bad), TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _indestructible(e, p, defn):
    cid = next(c for c in e.bz_tops(p) if e.cdef(c).id == defn)
    return e.chars(cid).get("indestructible") is True


def _drive(e, plays0=(), plays1=(), attacker=None, attacker_player=1,
           blocker=None, pick=None, stop=None, limit=1200):
    """汎用ドライバ（第401弾と同型を両プレイヤーの play と
    対象選択 pick に対応させたもの）。"""
    state = {"attacked": False, "played": []}
    plays = {0: list(plays0), 1: list(plays1)}
    for _ in range(limit):
        if stop is not None and stop():
            return state
        d = e.advance()
        if d is None:
            return state
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        pl = d.get("player")
        if kind == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d.get("min", 0))))
        elif kind == "main" and pl in plays and plays[pl]:
            hit = next((k for k in plays[pl] if k in keys), None)
            if hit is not None:
                plays[pl].remove(hit)
                state["played"].append(hit)
                e.answer([keys.index(hit)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind in ("attack", "declare_attack"):
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and pl == attacker_player \
                    and not state["attacked"]:
                state["attacked"] = True
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind in ("block", "declare_block"):
            hit = [i for i, k in enumerate(keys)
                   if blocker and k.startswith(f"bz:{blocker}:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("limit reached")


def _play_source(e):
    """p0 が T1169 を出し、出た時誘発が解決するまで進める
    （相手ターンに入った時点で解決済み）。"""
    _drive(e, plays0=["play:T1169"], stop=lambda: e.s.turn >= 2)
    assert "T1169" in _defns(e, "bz", 0)


def test_destroy_effect_blocked_during_window(rules):
    """実挙動: 光マナ7枚で出た時、自分のクリーチャー
    （味方 T001・発生源自身）は特性として indestructible
    を持ち、相手の破壊呪文（T056）でも破壊されない。"""
    e = _build(rules,
               {"bz": ["T001"], "hand": ["T1169"],
                "mana": ["T1117"] * 7},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    _play_source(e)
    assert _indestructible(e, 0, "T001")
    assert _indestructible(e, 0, "T1169")
    _drive(e, plays1=["play:T056"], pick="bz:T001",
           stop=lambda: "T056" in _defns(e, "graveyard", 1))
    assert "T001" in _defns(e, "bz", 0)          # 破壊されない
    assert "T1169" in _defns(e, "bz", 0)
    assert "T001" not in _defns(e, "graveyard", 0)


def test_battle_loss_blocked_during_window(rules):
    """実挙動: 味方ブロッカー（T004、3000）がパワー
    7000（T1118）の攻撃をブロックしてバトルに負けて
    も、期間中は破壊されない。"""
    e = _build(rules,
               {"bz": ["T004"], "hand": ["T1169"],
                "mana": ["T1117"] * 7},
               {"bz": ["T1118"]})
    _play_source(e)
    st = _drive(e, attacker="T1118", attacker_player=1,
                blocker="T004", stop=lambda: e.s.turn >= 3)
    assert st["attacked"]
    assert "T004" in _defns(e, "bz", 0)          # バトルで負けても残る
    assert "T1118" in _defns(e, "bz", 1)


def test_blocker_dies_without_source(rules):
    """対照: 発生源がいなければ、同じブロックで
    T004 はバトルに負けて破壊される。"""
    e = _build(rules, {"bz": ["T004"]}, {"bz": ["T1118"]})
    st = _drive(e, attacker="T1118", attacker_player=1,
                blocker="T004",
                stop=lambda: "T004" in _defns(e, "graveyard", 0))
    assert st["attacked"]
    assert "T004" in _defns(e, "graveyard", 0)
    assert "T004" not in _defns(e, "bz", 0)


def test_condition_unmet_no_protection(rules):
    """判別: 光マナが6枚（合計7枚でも条件未達）では
    誘発は解決しても効果は付かず、味方（T004）は
    相手の破壊呪文で破壊される。"""
    e = _build(rules,
               {"bz": ["T004"], "hand": ["T1169"],
                "mana": ["T1117"] * 6 + ["T001"]},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    _play_source(e)
    assert not _indestructible(e, 0, "T004")
    _drive(e, plays1=["play:T056"], pick="bz:T004",
           stop=lambda: "T056" in _defns(e, "graveyard", 1))
    assert "T004" in _defns(e, "graveyard", 0)   # 破壊される
    assert "T1169" in _defns(e, "bz", 0)


def test_window_expires_at_next_own_turn_start(rules):
    """実挙動（期間判別）: 保護は次の自分のターンの
    はじめまで。相手ターン中は有効で、自分のターンが
    再び始まった後は失効し、その後の相手の破壊呪文で
    味方（T001）は破壊される。"""
    e = _build(rules,
               {"bz": ["T001"], "hand": ["T1169"],
                "mana": ["T1117"] * 7},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    _play_source(e)
    assert _indestructible(e, 0, "T001")         # 相手ターン中有効
    _drive(e, stop=lambda: e.s.turn >= 4)        # 自分のターンを挟む
    assert not _indestructible(e, 0, "T001")     # 失効
    _drive(e, plays1=["play:T056"], pick="bz:T001",
           stop=lambda: "T056" in _defns(e, "graveyard", 1))
    assert "T001" in _defns(e, "graveyard", 0)   # 破壊される


def test_late_entry_not_in_resolution_set(rules):
    """判別（一括 modify の集合固定）: 出た時誘発の
    解決後にバトルゾーンに出たクリーチャー（同じ
    メインで続けて出した T004）は対象に含まれず、
    相手の破壊呪文で破壊される。発生源自身は守られる
    （dm23sd2-013 の非 dynamic な一括 modify の作法）。"""
    e = _build(rules,
               {"hand": ["T1169", "T004"], "mana": ["T1117"] * 10},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    _drive(e, plays0=["play:T1169", "play:T004"],
           stop=lambda: e.s.turn >= 2)
    assert "T004" in _defns(e, "bz", 0)
    assert _indestructible(e, 0, "T1169")
    assert not _indestructible(e, 0, "T004")     # 解決後の登場は対象外
    _drive(e, plays1=["play:T056"], pick="bz:T004",
           stop=lambda: "T056" in _defns(e, "graveyard", 1))
    assert "T004" in _defns(e, "graveyard", 0)
    assert "T1169" in _defns(e, "bz", 0)


def test_opponent_creatures_not_protected(rules):
    """判別（owner: you の範囲）: 期間中でも相手の
    クリーチャーは守られない。自分の単体破壊呪文
    （T620）で相手の T001 は破壊される。"""
    e = _build(rules,
               {"bz": ["T004"], "hand": ["T1169", "T620"],
                "mana": ["T1117"] * 7 + ["T620"] * 3},
               {"bz": ["T001"]})
    _drive(e, plays0=["play:T1169", "play:T620"], pick="bz:T001",
           stop=lambda: "T620" in _defns(e, "graveyard", 0))
    assert "T001" in _defns(e, "graveyard", 1)   # 相手は破壊される
    assert "T004" in _defns(e, "bz", 0)
    assert "T1169" in _defns(e, "bz", 0)
