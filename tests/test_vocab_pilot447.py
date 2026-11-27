"""語彙パイロット第447弾: attack_target_power_filter
（ドリフト）。

センサス（rejects 1,884件を取り直し）: pure
1,736件（974家族）/ multi 130件 / 空 gaps 18件。
pure の大半は範囲外（gr_summon 147 / aura 108
＝未承認 / hyperdimensional_zone 105 /
dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜446弾）と残置群（graveyard_replacement
残り dm25ex2-cho021、battle_opponent_reference
残り dmr01-049、untap_restriction 残り2件、
does_not_untap 残り dm25ex2-031、revolution_2
残り dm26sd1-o004、cast_limit_once_per_turn の
multi 2件、summoning_attack_rule 残り
dmex07-s01、entered_turn_attack 残り
dmbd11-d05、madness 残り dmx26-028、
after_battle_trigger 残り dmrp09-074、次点の
destroyed_this_turn_condition /
count_cards_drawn_this_turn /
player_not_attacked_while_tapped /
mana_tap_placement、後続候補の
distinct_civ_count、新規語彙候補 first_time_tap
/ turn_history_entry / played_free_condition、
専用ステージ送りの s_trigger_suppression /
power_threshold_keyword_gain）は覆す根拠が
無く再提案しない。

範囲内・最小の **attack_target_power_filter
（pure 1件、multi にも現れない）** を選定した。
対象は dmr15-030 勇気伝承 ゲット Jr.。第446弾で
「gap 名は power だが公式はコスト制限で
第444弾の登録形と同形＝表現可能」と評価され
次点に残置されていた候補。公式テキストは
マナ武装2条項:
- マナ武装 3: 火マナ3枚以上で「コスト4以下の
  クリーチャーに攻撃されない」
- マナ武装 5: 火マナ5枚以上で「パワー
  アタッカー+4000」と「W・ブレイカー」を得る
行の注記「攻撃者のコスト制限を表す語彙が無い」
は陳腐化。両条項とも既存部品の組み合わせ:
- マナ武装条件 if {cmp: [{count: {zone: mana,
  owner: you, filter: {civs: [fire]}}}, ">=", N]}
  は登録済みマナ武装カードの確立形
  （dm26rp2-028 等、登録済み149件）。
- 第1条項は第444弾の登録形 static {affects:
  self, if: 条件, mod: {deny: [{action:
  be_attacked, other: {cost_le: 4}}]}}。
- 第2条項は power_when {amount: 4000, when:
  attacking}（パワーアタッカーの定型所有形、
  第444弾 T1235 の先例）＋ grant
  [double_breaker] を、dm26rp2-028 の
  {power, grant} 単一 static の先例に倣い
  1つの static に併記する。
新規語彙・エンジン・defs・スキーマ変更なし
＝ドリフト。

partial は断片のみの stub（text は第1条項の
断片のみ、abilities 未構築、unsupported は
本 gap 1件のみ）。**補完あり: text（公式全文）
＋abilities（static 2件）**。alias は
dmr15-030d / promoy13-066（いずれも canon は
対象自身、identity 実測済み）。

公式境界: マナ武装は常在条件で、火を含む
多色カードも数える。条件を満たさなければ
両条項とも無効。「攻撃されない」は攻撃先の
合法性だけを制限する。パワーアタッカーは
攻撃中のみ+4000。

proto T1238（dmr15-030 型）。判別役は既存の
T282（自然 / コスト4・パワー3000＝境界の
攻撃役／バトル相手）/ T466（自然 / コスト5・
パワー3000＝制限外の攻撃役）/ T468（火＝
マナ役）/ T001（自然＝非火マナ役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の作法）。
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

MANA3 = {"cmp": [{"count": {"zone": "mana", "owner": "you",
                            "filter": {"civs": ["fire"]}}}, ">=", 3]}
MANA5 = {"cmp": [{"count": {"zone": "mana", "owner": "you",
                            "filter": {"civs": ["fire"]}}}, ">=", 5]}
DENY_STATIC = {"kind": "static", "affects": "self", "if": MANA3,
               "mod": {"deny": [{"action": "be_attacked",
                                  "other": {"cost_le": 4}}]}}
GRANT_STATIC = {"kind": "static", "affects": "self", "if": MANA5,
                "mod": {"power_when": {"amount": 4000,
                                        "when": "attacking"},
                        "grant": ["double_breaker"]}}

NAME = "勇気伝承 ゲット Jr."
TEXT = ("マナ武装 ３：自分のマナゾーンに火のカードが３枚以上あれば、"
        "このクリーチャーはコスト４以下のクリーチャーに攻撃されない。"
        "マナ武装 ５：自分のマナゾーンに火のカードが５枚以上あれば、"
        "このクリーチャーは「パワーアタッカー+4000」と「W・ブレイカー」を得る。")
FORM = {"name": NAME, "types": ["creature"],
        "civs": ["fire"], "cost": 2, "power": 2000,
        "races": ["ヒューマノイド爆"], "mana": 1,
        "text": TEXT, "abilities": [DENY_STATIC, GRANT_STATIC]}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1238")
    for k, v in FORM.items():
        assert c[k] == v, k
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.name == NAME
    plain = [a for a in d.abilities if "keyword" not in a]
    assert plain == FORM["abilities"]


def test_form_def_errors():
    base = {"id": "X447", **copy.deepcopy(FORM)}
    parse_card(copy.deepcopy(base), TABLES)
    # deny 項目の未知アクション
    bad = copy.deepcopy(base)
    bad["abilities"][0]["mod"]["deny"][0]["action"] = "be_attackedd"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # deny 項目の未知キー
    bad = copy.deepcopy(base)
    bad["abilities"][0]["mod"]["deny"][0]["foo"] = 1
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # other フィルタの未知キー
    bad = copy.deepcopy(base)
    bad["abilities"][0]["mod"]["deny"][0]["other"] = {"cost_lee": 4}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # 未知の mod キー
    bad = copy.deepcopy(base)
    bad["abilities"][1]["mod"]["grantt"] = []
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


# ---------- ドライバ ----------

def _keys(d):
    return [o.get("key") for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif d["kind"] in ("declare_strigger", "declare_sback"):
        e.answer([])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _drive(e, attacks=(), arrange=None, stop=None, limit=1500):
    """attacks（攻撃キーの列）を順に一度ずつ実行する。
    攻撃判断の選択肢は st["attack_options"] に
    （player, keys）で記録する。"""
    st = {"done": [], "attack_options": []}
    queue = list(attacks)
    for _ in range(limit):
        if stop and stop():
            return st
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if arrange:
            arrange(e, d)
        if d["kind"] == "attack":
            st["attack_options"].append((d.get("player"), keys))
        if queue and d["kind"] == "attack" and queue[0] in keys:
            e.answer([keys.index(queue[0])])
            st["done"].append(queue.pop(0))
            continue
        _answer_default(e, d)
    raise AssertionError("driver limit reached")


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    # bz は共有ゾーンなのでコントローラーまで見て引く
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn
                and e.s.cards[c].controller == p)


def _zone(e, cid):
    return e.s.cards[cid].zone


def _tap_on_turn(e, p, defn):
    """p のターン中、その側の defn をタップ状態に保つ。
    タップは charge / main の判断でのみ行う
    （第442弾の作法）。"""
    def arrange(eng, d):
        if eng.s.active == p and d["kind"] in ("charge", "main"):
            for c in eng.zlist("bz", p):
                if eng.s.cards[c].defn == defn \
                        and eng.s.cards[c].controller == p:
                    eng.s.cards[c].tapped = True
    return arrange


def _attack_keys(st, player, attacker):
    out = []
    for p, keys in st["attack_options"]:
        if p == player:
            out += [k for k in keys
                    if k and k.startswith(f"attack:{attacker}:")]
    return out


FIRE_MANA = "T468"   # 火（マナ役）
OTHER_MANA = "T001"  # 自然（非火マナ役）


# ---------- 実挙動: 第1条項（マナ武装 3） ----------

def test_mana3_cost4_attacker_cannot_attack(rules):
    """火マナ3枚（境界）: コスト4の T282 は T1238 を
    攻撃できない。攻撃判断の選択肢に
    attack:T282:T1238 が現れず、プレイヤーへの
    攻撃は通常どおりできてシールドが1枚割れる。
    T1238 は場に残る。"""
    e = _build(rules,
               {"bz": ["T1238"], "mana": [FIRE_MANA] * 3},
               {"bz": ["T282"]})
    src = _cid(e, 0, "T1238")
    st = _drive(e, attacks=["attack:T282:player"],
                arrange=_tap_on_turn(e, 0, "T1238"),
                stop=lambda: len(e.zlist("shield", 0)) <= 4)
    assert st["done"] == ["attack:T282:player"]
    keys = _attack_keys(st, 1, "T282")
    assert "attack:T282:player" in keys
    assert "attack:T282:T1238" not in keys
    assert len(e.zlist("shield", 0)) == 4
    assert _zone(e, src) == "bz"


def test_mana2_cost4_attacker_can_attack(rules):
    """火マナ2枚（条件未達）: コスト4の T282 は
    T1238 を攻撃でき、バトル（3000 vs 2000）で
    T1238 は破壊される。"""
    e = _build(rules,
               {"bz": ["T1238"], "mana": [FIRE_MANA] * 2},
               {"bz": ["T282"]})
    src = _cid(e, 0, "T1238")
    atk = _cid(e, 1, "T282")
    st = _drive(e, attacks=["attack:T282:T1238"],
                arrange=_tap_on_turn(e, 0, "T1238"),
                stop=lambda: _zone(e, src) == "graveyard")
    assert st["done"] == ["attack:T282:T1238"]
    assert _zone(e, atk) == "bz"


def test_nonfire_mana_does_not_count(rules):
    """マナ総数5枚でも火が2枚なら条件未達:
    非火マナ（自然）は数えない。コスト4の T282 は
    T1238 を攻撃でき、バトルで破壊される。"""
    e = _build(rules,
               {"bz": ["T1238"],
                "mana": [FIRE_MANA] * 2 + [OTHER_MANA] * 3},
               {"bz": ["T282"]})
    src = _cid(e, 0, "T1238")
    st = _drive(e, attacks=["attack:T282:T1238"],
                arrange=_tap_on_turn(e, 0, "T1238"),
                stop=lambda: _zone(e, src) == "graveyard")
    assert st["done"] == ["attack:T282:T1238"]


def test_mana3_cost5_attacker_can_attack(rules):
    """火マナ3枚でも、コスト5の T466 は制限の
    対象外で T1238 を攻撃でき、バトル
    （3000 vs 2000）で破壊される。"""
    e = _build(rules,
               {"bz": ["T1238"], "mana": [FIRE_MANA] * 3},
               {"bz": ["T466"]})
    src = _cid(e, 0, "T1238")
    atk = _cid(e, 1, "T466")
    st = _drive(e, attacks=["attack:T466:T1238"],
                arrange=_tap_on_turn(e, 0, "T1238"),
                stop=lambda: _zone(e, src) == "graveyard")
    assert st["done"] == ["attack:T466:T1238"]
    assert _zone(e, atk) == "bz"


# ---------- 実挙動: 第2条項（マナ武装 5） ----------

def test_mana5_power_attacker_and_double_breaker(rules):
    """火マナ5枚: パワーアタッカー+4000 で
    タップした T282（3000）をバトル中6000で
    破壊して場に残り、翌ターンのプレイヤー攻撃で
    シールドを2つブレイクする（W・ブレイカー）。"""
    e = _build(rules,
               {"bz": ["T1238"], "mana": [FIRE_MANA] * 5},
               {"bz": ["T282"]})
    src = _cid(e, 0, "T1238")
    tgt = _cid(e, 1, "T282")
    e.s.cards[tgt].tapped = True
    st = _drive(e, attacks=["attack:T1238:T282",
                            "attack:T1238:player"],
                stop=lambda: len(e.zlist("shield", 1)) <= 3)
    assert st["done"] == ["attack:T1238:T282",
                          "attack:T1238:player"]
    assert _zone(e, tgt) == "graveyard"
    assert _zone(e, src) == "bz"
    assert len(e.zlist("shield", 1)) == 3


def test_mana4_no_power_attacker(rules):
    """火マナ4枚（第2条項は未達）: パワー
    アタッカーは得ず、タップした T282（3000）
    とのバトルは 2000 で負けて T1238 は
    破壊される（第1条項の条件は満たすが
    バトルには無関係）。"""
    e = _build(rules,
               {"bz": ["T1238"], "mana": [FIRE_MANA] * 4},
               {"bz": ["T282"]})
    src = _cid(e, 0, "T1238")
    tgt = _cid(e, 1, "T282")
    e.s.cards[tgt].tapped = True
    st = _drive(e, attacks=["attack:T1238:T282"],
                stop=lambda: _zone(e, src) == "graveyard")
    assert st["done"] == ["attack:T1238:T282"]
    assert _zone(e, tgt) == "bz"


def test_mana4_single_break(rules):
    """火マナ4枚: W・ブレイカーも得ず、
    プレイヤー攻撃のブレイクは1枚だけ。"""
    e = _build(rules,
               {"bz": ["T1238"], "mana": [FIRE_MANA] * 4},
               {"bz": ["T001"]})
    src = _cid(e, 0, "T1238")
    st = _drive(e, attacks=["attack:T1238:player"],
                stop=lambda: len(e.zlist("shield", 1)) <= 4)
    assert st["done"] == ["attack:T1238:player"]
    assert len(e.zlist("shield", 1)) == 4
    assert _zone(e, src) == "bz"
