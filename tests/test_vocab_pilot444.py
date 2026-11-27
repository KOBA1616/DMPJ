"""語彙パイロット第444弾: attacker_cost_restriction
（ドリフト）。

センサス（rejects 1,888件を取り直し）: pure は
1〜4件の小家族が多数で、大半は範囲外（gr_summon
147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift
4）。評価済み却下（第316〜320・355〜443弾）と残置群
（graveyard_replacement 残り dm25ex2-cho021、
battle_opponent_reference 残り dmr01-049、
untap_restriction 残り2件、does_not_untap 残り
dm25ex2-031、revolution_2 残り dm26sd1-o004、
cast_limit_once_per_turn の multi 2件、
summoning_attack_rule 残り dmex07-s01、
entered_turn_attack 残り dmbd11-d05、madness 残り
dmx26-028、after_battle_trigger 残り dmrp09-074、
s_trigger_suppression＝専用ステージ送り、次点の
destroyed_this_turn_condition /
count_cards_drawn_this_turn /
player_not_attacked_while_tapped /
mana_tap_placement、後続候補の distinct_civ_count、
新規語彙候補 first_time_tap / turn_history_entry /
played_free_condition）は覆す根拠が無く再提案
しない。本弾で個別に評価して見送った候補:
shield_face_up_spell（pure 2。表向きシールドの
束への着地＋条件の複合）、
only_from_hand_play_restriction（pure 2。複合 /
G-NEO 進化つきで重い）、face_down_shield
（pure 2。bz→shield の裏向き着地整備が未確認）、
entry_leave_protection（pure 2。全置換は置換
走査の設計判断に触れる）、source_restriction
（pure 2。発生源フィルタ未確立）、
hand_shield_recycle（pure 2。入れ替え複合）、
break_pre_event（pure 2。ブレイク前の割り込み
未確立）、name_or_filter（pure 2。名前部分一致
OR フィルタ未確立＋複合）、untap_by_tapping_mana
（pure 1。ターン開始処理の複合）、
untap_unless_destroy（pure 1。支払い型で未確立）。

範囲内・最小の **attacker_cost_restriction
（pure 2件）** を選定した。対象は dmr05-098
ヨケッピ・チョーナン と dmr06-028 ボルカニック・
ザウルス。両行の注記「攻撃者のコスト制限を表す
語彙が無い」は陳腐化: 条項「このクリーチャーは
コスト6以下のクリーチャーに攻撃されない」は
static {affects: self, mod: {deny: [{action:
be_attacked, other: {cost_le: 6}}]}} で表せる。
- deny の辞書形＋other フィルタは既存部品:
  defs は {action, other, ...} を検証し、
  combat.h_attack は permits（攻撃先,
  "be_attacked", 攻撃側）で other を攻撃側に
  当てる。登録先例 dm01-009「パワー4000以下の
  クリーチャーにブロックされない」= deny
  [{action: be_blocked, other: {power_le: 4000}}]
  が鏡像の確立形。
- rustcore も {action, other} の deny
  （be_blocked / be_attacked、simple filter）を
  明示対応し、cost_le は _FILTER_INTS に含まれる。
新規語彙・エンジン・defs・スキーマ変更なし
＝ドリフト（be_attacked への other フィルタ
適用は既存部品の初使用）。

dmr05-098 の partial は骨格完備（text 公式全文、
keywords [speed_attacker]）で abilities 未構築、
unsupported は本条項1件のみ。**補完あり:
abilities**（static 1件）。dmr06-028 の partial
は骨格完備（text 公式全文、keywords
[double_breaker]）で、パワーアタッカーが
attack trigger＋modify {power: 2000}
（end_of_turn）の下書き形だが、split の定型
所有形は static {affects: self, mod:
{power_when: {amount: 2000, when: attacking}}}
（登録済み186件の確立形。trigger 形はバトル
後も残り攻撃のたびに重なるため公式と食い違う）
＝提出形は定型所有形に置き換える。**補完あり:
abilities**（power_when static への置き換え＋
deny static の追加）。alias は両件とも無し
（identity 実測で canon は対象自身）。

公式境界: 「攻撃されない」は攻撃先の合法性
だけを制限し、ブロックは通常どおり可能で、
プレイヤー攻撃も制限しない。コストは攻撃側
クリーチャーの特性（印刷コスト）で判定し、
境界は6以下＝コスト6は攻撃できず、コスト7は
攻撃できる。

proto T1234（dmr05-098 型）/ T1235
（dmr06-028 型）。判別役は既存の T021
（コスト6＝境界・パワー5000）/ T040（コスト7・
パワー6000）/ T004（ブロッカー・パワー3000）。

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

DENY_STATIC = {"kind": "static", "affects": "self",
               "mod": {"deny": [{"action": "be_attacked",
                                 "other": {"cost_le": 6}}]}}

NAME_A = "ヨケッピ・チョーナン"
TEXT_A = ("スピードアタッカー(このクリーチャーは召喚酔いしない)\n"
          "このクリーチャーはコスト６以下のクリーチャーに攻撃されない。")
ABILITIES_A = [DENY_STATIC]
FORM_A = {"name": NAME_A, "types": ["creature"],
          "civs": ["fire"], "cost": 4, "power": 2000,
          "races": ["ファイアー・バード", "ハンター"], "mana": 1,
          "keywords": ["speed_attacker"],
          "text": TEXT_A, "abilities": ABILITIES_A}

NAME_B = "ボルカニック・ザウルス"
TEXT_B = ("パワーアタッカー+2000(攻撃中、このクリーチャーのパワーは+2000される)\n"
          "W・ブレイカー(このクリーチャーはシールドを２枚ブレイクする)\n"
          "このクリーチャーは、コスト６以下のクリーチャーに攻撃されない。")
ABILITIES_B = [
    {"kind": "static", "affects": "self",
     "mod": {"power_when": {"amount": 2000, "when": "attacking"}}},
    DENY_STATIC,
]
FORM_B = {"name": NAME_B, "types": ["creature"],
          "civs": ["fire"], "cost": 5, "power": 4000,
          "races": ["ロック・ビースト"], "mana": 1,
          "keywords": ["double_breaker"],
          "text": TEXT_B, "abilities": ABILITIES_B}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    for tid, form in (("T1234", FORM_A), ("T1235", FORM_B)):
        c = proto_card(tid)
        for k, v in form.items():
            assert c[k] == v, (tid, k)
        d = parse_card(copy.deepcopy(c), TABLES)
        assert d.name == form["name"]
        # キーワード由来の static（keyword マーカーつき）を除いた
        # 残りが FORM の abilities と一致する（deny の辞書形は
        # 正規化されずそのまま格納される）
        plain = [a for a in d.abilities if "keyword" not in a]
        assert plain == form["abilities"]


def test_form_def_errors():
    base = {"id": "X444", **copy.deepcopy(FORM_A)}
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
    bad["abilities"][0]["mod"]["deny"][0]["other"] = {"cost_lee": 6}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # 未知の mod キー
    bad = copy.deepcopy(base)
    bad["abilities"][0]["mod"]["denyy"] = []
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


def _drive(e, attacks=(), arrange=None, finish_player=None,
           block=False, limit=1500):
    """attacks（攻撃キーの列）を順に一度ずつ実行する。
    攻撃判断の選択肢は st["attack_options"] に
    （player, keys）で記録する。block=True の時は
    ブロック判断で no_block 以外を選ぶ。
    finish_player のチャージ判断が来たら答えずに止める。"""
    st = {"done": [], "attack_options": [], "blocked": False}
    queue = list(attacks)
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if arrange:
            arrange(e, d)
        if not queue and finish_player is not None \
                and d["kind"] == "charge" \
                and d.get("player") == finish_player:
            return st
        if d["kind"] == "attack":
            st["attack_options"].append((d.get("player"), keys))
        if d["kind"] == "block" and block:
            pick = next(k for k in keys if k != "no_block")
            e.answer([keys.index(pick)])
            st["blocked"] = True
            continue
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


def _tap_on_opp_turn(e, p, defn):
    """相手（p）のターン中、その側の defn をタップ状態に
    保つ。タップは charge / main の判断でのみ行う
    （第442弾の作法）。"""
    def arrange(eng, d):
        if eng.s.active == p and d["kind"] in ("charge", "main"):
            for c in eng.zlist("bz", p):
                if eng.s.cards[c].defn == defn \
                        and eng.s.cards[c].controller == p:
                    eng.s.cards[c].tapped = True
    return arrange


def _opp_attack_keys(st, player, attacker):
    """記録した攻撃判断から、そのプレイヤーの attacker の
    選択肢キーをすべて集める。"""
    out = []
    for p, keys in st["attack_options"]:
        if p == player:
            out += [k for k in keys
                    if k and k.startswith(f"attack:{attacker}:")]
    return out


# ---------- dmr05-098 型（T1234） ----------

def test_cost6_attacker_cannot_attack_but_can_attack_player(rules):
    """コスト6の T021（境界）はタップした T1234 を
    攻撃できないが、プレイヤーは攻撃できる:
    T1234 がプレイヤーを攻撃してタップした後、
    T021 の攻撃選択肢に attack:T021:T1234 が無く
    attack:T021:player があり、実行すると自分の
    シールドが1枚割れる。T1234 は場に残る。"""
    e = _build(rules, {"bz": ["T1234"]}, {"bz": ["T021"]})
    tgt = _cid(e, 0, "T1234")
    st = _drive(e, attacks=["attack:T1234:player",
                            "attack:T021:player"],
                finish_player=0)
    assert st["done"] == ["attack:T1234:player",
                          "attack:T021:player"]
    keys = _opp_attack_keys(st, 1, "T021")
    assert "attack:T021:T1234" not in keys
    assert "attack:T021:player" in keys
    assert _zone(e, tgt) == "bz"
    assert len(e.zlist("shield", 0)) == 4


def test_cost7_attacker_can_attack(rules):
    """コスト7の T040 はタップした T1234 を攻撃
    できる: 選択肢に attack:T040:T1234 があり、
    バトル（6000 vs 2000）で T1234 は破壊され、
    T040 は場に残る（境界の判別）。"""
    e = _build(rules, {"bz": ["T1234"]}, {"bz": ["T040"]})
    tgt = _cid(e, 0, "T1234")
    atk = _cid(e, 1, "T040")
    st = _drive(e, attacks=["attack:T1234:player",
                            "attack:T040:T1234"],
                finish_player=0)
    assert st["done"] == ["attack:T1234:player",
                          "attack:T040:T1234"]
    keys = _opp_attack_keys(st, 1, "T040")
    assert "attack:T040:T1234" in keys
    assert _zone(e, tgt) == "graveyard"
    assert _zone(e, atk) == "bz"


def test_protected_creature_can_be_blocked(rules):
    """deny は be_attacked だけなので、T1234 の
    攻撃は通常どおりブロックされる: ブロッカー
    T004（3000）がブロックし、バトルで T1234
    （2000）は破壊される。"""
    e = _build(rules, {"bz": ["T1234"]}, {"bz": ["T004"]})
    src = _cid(e, 0, "T1234")
    blk = _cid(e, 1, "T004")
    st = _drive(e, attacks=["attack:T1234:player"],
                block=True, finish_player=1)
    assert st["done"] == ["attack:T1234:player"]
    assert st["blocked"]
    assert _zone(e, src) == "graveyard"
    assert _zone(e, blk) == "bz"
    assert len(e.zlist("shield", 1)) == 5


# ---------- dmr06-028 型（T1235） ----------

def test_t1235_power_attacker_beats_cost6(rules):
    """T1235 がタップした T021（5000）を攻撃:
    power_when で攻撃中6000になり T021 を破壊
    して場に残る（partial の trigger 下書き形
    ではなく定型所有の power_when 形であることの
    判別を兼ねる）。"""
    e = _build(rules, {"bz": ["T1235"]}, {"bz": ["T021"]})
    src = _cid(e, 0, "T1235")
    tgt = _cid(e, 1, "T021")
    st = _drive(e, attacks=["attack:T1235:T021"],
                arrange=_tap_on_opp_turn(e, 1, "T021"),
                finish_player=1)
    assert st["done"] == ["attack:T1235:T021"]
    assert _zone(e, tgt) == "graveyard"
    assert _zone(e, src) == "bz"


def test_t1235_cost6_attacker_cannot_attack(rules):
    """T1235 も同じ deny を持つ: プレイヤーを
    攻撃してタップした T1235 を、コスト6の
    T021 は攻撃できない（プレイヤー攻撃は可能）。"""
    e = _build(rules, {"bz": ["T1235"]}, {"bz": ["T021"]})
    tgt = _cid(e, 0, "T1235")
    st = _drive(e, attacks=["attack:T1235:player",
                            "attack:T021:player"],
                finish_player=0)
    assert st["done"] == ["attack:T1235:player",
                          "attack:T021:player"]
    keys = _opp_attack_keys(st, 1, "T021")
    assert "attack:T021:T1235" not in keys
    assert "attack:T021:player" in keys
    assert _zone(e, tgt) == "bz"
