"""語彙パイロット第442弾: destroy_attack_target_without_battle
（ドリフト）。

センサス（rejects 1,890件を取り直し）: pure は
1〜4件の小家族が多数で、大半は範囲外（gr_summon
147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift
4）。評価済み却下（第316〜320・355〜441弾）と残置群
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
player_not_attacked_while_tapped、後続候補の
distinct_civ_count、新規語彙候補 first_time_tap /
turn_history_entry / played_free_condition）は
覆す根拠が無く再提案しない。本弾で個別に評価して
見送った候補: cancel_attack（pure 3。op は確立
済みだが残り3件は異形の複合でファミリーとして
最小にならない）、look_reorder（pure 2。汎用の
「見る」op は無く mekurade 専用）、
shuffle_own_shields（pure 1。shuffle は山札専用）、
slayer_while_attacking_low_cost、
summon_cost_reduction_by_choosing_cards、
override_cannot_attack_for_player_attack、
mana_tap_placement（次点として残置）。

範囲内・最小の **destroy_attack_target_without_battle
（pure 1件）の dm20-028 のみ** を選定した。行の注記
「バトルの前に破壊してバトル自体を行わない効果を
表す語彙が無い」は陳腐化:
- 第1条項は trigger {when: {event: attack,
  subject: self, target: "creature"}, effect:
  [destroy {select: {ref: event.target}}]}。
  subject: self ＋ event.target 参照は登録済み
  dmd15-009 の確立形。target: "creature" は defs の
  検証許可値で _match_when 実装済み・schema.py は
  無制限（新規語彙ではなく既存部品の初使用）。
- 第2条項は trigger {when: {event: attack,
  target: self}, effect: [destroy {select:
  {ref: self}}]}。when {event: attack, target:
  self} は登録済み17件の確立形。
- 「(バトルは行われない)」に専用 op は要らない:
  攻撃宣言時の誘発はブロック宣言より前に解決
  され、攻撃側・攻撃先が場に無ければ
  combat.h_attack の既存チェック（505.6a 相当）が
  ブロック宣言自体を経ずに攻撃を終わらせる。
  cancel_attack（第251弾）を併記すると、破壊が
  置換・無効化された場合にも攻撃が止まって公式と
  食い違うため併記しない。

対象は dm20-028 エンドブリンガー・ドラグーン
（闇 / コスト3 / パワー2000 / 種族 ティラノ・
ドレイク、mana 1）。partial は骨格完備（text は
公式全文、keywords 無し）で abilities 未構築、
unsupported は本 gap 1件のみ（text は第1条項
だけだが第2条項も同一機構で構築）。**補完あり:
abilities**（trigger 2件とも）。alias 無し
（identity 実測で canon は対象自身）。

結論はドリフト（追加語彙・エンジン・defs・
スキーマ変更なし）。公式境界: 破壊は攻撃宣言時
（ブロック宣言前）に解決され、対象が破壊され
れば攻撃は対象を失って終了しブロック宣言も
できない。破壊は任意ではない。プレイヤー攻撃
時は第1条項は発火しない。

proto T1232（dm20-028 型）。判別役は既存の
T001（パワー2000＝バトルなら相打ち）/ T004
（ブロッカー）/ T008（パワー1000＝バトルなら
負ける攻撃役）/ T163（破壊不能）。

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
NAME = "エンドブリンガー・ドラグーン"
FULL_TEXT = ("このクリーチャーがクリーチャーを攻撃する時、"
             "そのクリーチャーを破壊する。(バトルは行われない)\n"
             "このクリーチャーが攻撃された時、"
             "このクリーチャーを破壊する。(バトルは行われない)")

ABILITIES = [
    {"kind": "trigger",
     "when": {"event": "attack", "subject": "self",
              "target": "creature"},
     "effect": [{"op": "destroy",
                 "select": {"ref": "event.target"}}]},
    {"kind": "trigger",
     "when": {"event": "attack", "target": "self"},
     "effect": [{"op": "destroy",
                 "select": {"ref": "self"}}]},
]

FORM = {"name": NAME, "types": ["creature"],
        "civs": ["darkness"], "cost": 3, "power": 2000,
        "races": ["ティラノ・ドレイク"], "mana": 1,
        "text": FULL_TEXT, "abilities": ABILITIES}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1232")
    for k, v in FORM.items():
        assert c[k] == v, k
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.name == NAME and d.power == 2000
    # destroy は move {to: graveyard, reason: destroy} に正規化
    assert d.abilities == [
        {"kind": "trigger",
         "when": {"event": "attack", "subject": "self",
                  "target": "creature"},
         "effect": [{"op": "move",
                     "select": {"ref": "event.target"},
                     "to": "graveyard", "reason": "destroy"}]},
        {"kind": "trigger",
         "when": {"event": "attack", "target": "self"},
         "effect": [{"op": "move",
                     "select": {"ref": "self"},
                     "to": "graveyard", "reason": "destroy"}]}]


def test_form_def_errors():
    base = {"id": "X442", **copy.deepcopy(FORM)}
    parse_card(copy.deepcopy(base), TABLES)
    # when の target の不正値
    bad = copy.deepcopy(base)
    bad["abilities"][0]["when"]["target"] = "creatur"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # when の未知イベント
    bad = copy.deepcopy(base)
    bad["abilities"][0]["when"]["event"] = "attackk"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # effect の未知 op
    bad = copy.deepcopy(base)
    bad["abilities"][0]["effect"][0]["op"] = "destroyy"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # フィルタの未知キー
    bad = copy.deepcopy(base)
    bad["abilities"][0]["effect"][0] = {
        "op": "destroy",
        "select": {"zone": "bz", "owner": "opp",
                   "filter": {"types": ["creature"],
                              "power_lee": 2000},
                   "count": 1}}
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
           limit=1500):
    """attacks（攻撃キーの列）を順に一度ずつ実行する。
    arrange(e, d) は各判断の前に呼ばれる（相手ターン中に
    攻撃対象をタップ状態に保つ等の調整用）。全攻撃が
    終わった後、finish_player のチャージ判断が来たら
    答えずに止める（攻撃ステップが完全に終わった観測点）。"""
    st = {"done": [], "block_offered": False}
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
        if d["kind"] == "block":
            st["block_offered"] = True
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
    保つ（ターン開始のアンタップを打ち消す調整）。
    タップは charge / main の判断でのみ行う: 攻撃判断の
    途中でタップすると、その判断の選択肢リストが再計算で
    縮んで応答インデックスがずれるため。"""
    def arrange(eng, d):
        if eng.s.active == p and d["kind"] in ("charge", "main"):
            for c in eng.zlist("bz", p):
                if eng.s.cards[c].defn == defn \
                        and eng.s.cards[c].controller == p:
                    eng.s.cards[c].tapped = True
    return arrange


# ---------- 第1条項: 攻撃する時に攻撃先を破壊 ----------

def test_clause1_destroys_target_and_no_battle(rules):
    """T1232（2000）がタップした T001（2000）を攻撃:
    宣言時に T001 が破壊され、バトルは行われない。
    バトルなら相打ちで両方破壊されるため、T1232 が
    場に残ることが判別になる。シールドも割れない。"""
    e = _build(rules, {"bz": ["T1232"]}, {"bz": ["T001"]})
    src = _cid(e, 0, "T1232")
    tgt = _cid(e, 1, "T001")
    st = _drive(e, attacks=["attack:T1232:T001"],
                arrange=_tap_on_opp_turn(e, 1, "T001"),
                finish_player=1)
    assert st["done"] == ["attack:T1232:T001"]
    assert _zone(e, tgt) == "graveyard"
    assert _zone(e, src) == "bz"
    assert e.s.cards[src].tapped
    assert len(e.zlist("shield", 1)) == 5


def test_clause1_block_window_never_opens(rules):
    """攻撃先が宣言時に破壊されれば、ブロック宣言
    自体が起きない: 相手のブロッカー T004 は
    ブロック判断を提示されず、アンタップのまま。"""
    e = _build(rules, {"bz": ["T1232"]},
               {"bz": ["T001", "T004"]})
    src = _cid(e, 0, "T1232")
    tgt = _cid(e, 1, "T001")
    blk = _cid(e, 1, "T004")
    st = _drive(e, attacks=["attack:T1232:T001"],
                arrange=_tap_on_opp_turn(e, 1, "T001"),
                finish_player=1)
    assert st["done"] == ["attack:T1232:T001"]
    assert _zone(e, tgt) == "graveyard"
    assert not st["block_offered"]
    assert not e.s.cards[blk].tapped
    assert _zone(e, src) == "bz"


def test_clause1_indestructible_target_battle_proceeds(rules):
    """破壊不能の T163（3000）が攻撃先なら破壊は
    通らず、バトルが通常どおり行われる（cancel_attack
    を併記しないことの判別）: T1232（2000）は
    バトルで負けて破壊され、T163 は場に残る。"""
    e = _build(rules, {"bz": ["T1232"]}, {"bz": ["T163"]})
    src = _cid(e, 0, "T1232")
    tgt = _cid(e, 1, "T163")
    st = _drive(e, attacks=["attack:T1232:T163"],
                arrange=_tap_on_opp_turn(e, 1, "T163"),
                finish_player=1)
    assert st["done"] == ["attack:T1232:T163"]
    assert _zone(e, tgt) == "bz"
    assert _zone(e, src) == "graveyard"


def test_clause1_player_attack_breaks_normally(rules):
    """プレイヤーを攻撃する時は第1条項は発火せず、
    通常どおりシールドを1枚ブレイクする
    （target: "creature" の判別）。"""
    e = _build(rules, {"bz": ["T1232"]}, {"bz": []})
    src = _cid(e, 0, "T1232")
    st = _drive(e, attacks=["attack:T1232:player"],
                finish_player=1)
    assert st["done"] == ["attack:T1232:player"]
    assert len(e.zlist("shield", 1)) == 4
    assert _zone(e, src) == "bz"
    assert e.zlist("graveyard", 0) == []
    assert e.zlist("graveyard", 1) == []


# ---------- 第2条項: 攻撃された時に自身を破壊 ----------

def test_clause2_destroys_self_and_attacker_survives(rules):
    """T008（1000）がタップした T1232（2000）を攻撃:
    宣言時に T1232 が自身を破壊し、バトルは行われ
    ない。バトルなら T008 が負けて破壊されるため、
    T008 が場に残ることが判別になる。"""
    e = _build(rules, {"bz": ["T1232"]}, {"bz": ["T008"]})
    src = _cid(e, 0, "T1232")
    atk = _cid(e, 1, "T008")
    st = _drive(e, attacks=["attack:T1232:player",
                            "attack:T008:T1232"],
                finish_player=0)
    assert st["done"] == ["attack:T1232:player",
                          "attack:T008:T1232"]
    assert _zone(e, src) == "graveyard"
    assert _zone(e, atk) == "bz"
    assert e.s.cards[atk].tapped
    assert len(e.zlist("shield", 0)) == 5


def test_clause2_not_fired_when_player_attacked(rules):
    """相手がプレイヤーを攻撃しても第2条項は
    発火しない: T1232 は場に残り、シールドが
    1枚ブレイクされる。"""
    e = _build(rules, {"bz": ["T1232"]}, {"bz": ["T008"]})
    src = _cid(e, 0, "T1232")
    st = _drive(e, attacks=["attack:T008:player"],
                finish_player=0)
    assert st["done"] == ["attack:T008:player"]
    assert _zone(e, src) == "bz"
    assert len(e.zlist("shield", 0)) == 4


def test_mirror_clause1_destroys_defending_copy(rules):
    """相打ち形の相互作用: 相手の T1232 が自分の
    タップした T1232 を攻撃すると、第1条項で
    防御側が破壊され攻撃は終わる（防御側の第2条項は
    発生源が既に墓地で不発）。攻撃側は場に残る。"""
    e = _build(rules, {"bz": ["T1232"]}, {"bz": ["T1232"]})
    mine = _cid(e, 0, "T1232")
    theirs = _cid(e, 1, "T1232")
    st = _drive(e, attacks=["attack:T1232:player",
                            "attack:T1232:T1232"],
                finish_player=0)
    assert st["done"] == ["attack:T1232:player",
                          "attack:T1232:T1232"]
    assert _zone(e, mine) == "graveyard"
    assert _zone(e, theirs) == "bz"
    assert len(e.zlist("shield", 0)) == 5
