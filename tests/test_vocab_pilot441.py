"""語彙パイロット第441弾: count_face_up_shields（ドリフト）。

センサス（rejects 1,891件を取り直し）: pure は
1〜4件の小家族が多数で、大半は範囲外（gr_summon
147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift
4）。評価済み却下（第316〜320・355〜440弾）と残置群
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
覆す根拠が無く再提案しない。

範囲内・最小の **count_face_up_shields（pure
1件）の dm23bd7-019 のみ** を選定した。行の注記
「表向きのシールドを数える語彙が無い」は陳腐化:
表向きシールドの**カード**数は第169弾の確立形
count {bundle_of: {zone: shield, owner: you},
filter: {face_up: true}}（proto T338。bundle_of
の候補は [トップ]＋その下すべてで、覆われた
表向きカードも数える＝第148弾の決定。束単位の
bundles 数えとは別）。「〜につき1枚引いても
よい」は登録済み dm21-024 の repeat {times:
{count: …}, body: [may [draw 1]]}（1枚ごとに
任意）。呪文面ビスティック・マースは登録済み
dm23bd7-026 グローリー・スノーと文面が完全一致
（S・トリガー＋同条項＋2枚）で、その登録形を
そのまま使う。

対象は dm23bd7-019 煌メク聖晶 弩楼 /
ビスティック・マース（ツインパクト: クリーチャー
面＝光 / コスト9 / パワー11500 / 種族 メタリカ/
サバキスト、呪文面＝光 / コスト4、mana 1）。
partial はクリーチャー面の骨格のみ（text は
条項だけの断片、keywords 未記載）で abilities
未構築、unsupported は本 gap 1件のみ。**補完
あり: text（両面の公式全文）＋keywords＋
abilities＋呪文面まるごと**。alias は
dmbd07-b-002（identity 実測で canon は対象自身、
rejects に独自行なし）。

結論はドリフト（追加語彙・エンジン・defs・
スキーマ変更なし）。公式境界: 数えるのは束では
なく表向きのカード（重なった下の表向きも数える）。
ドローは1枚ごとに任意。呪文面の条件は唱える
時点のマナ数比較で、同数・自分が多い場合は
何もしない。タップ指定は無いので置かれる
マナはアンタップ。

proto T1231（dm23bd7-019 型）。判別役は既存の
T337 / T338（表向きシールド系の原典）と
T001 / T002（通常カード）。

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
NAME = "煌メク聖晶 弩楼 / ビスティック・マース"
CREATURE_TEXT = ("ブロッカー\nW・ブレイカー\n"
                 "このクリーチャーが出た時、自分のシールドゾーンにある"
                 "表向きのカード１枚につき、カードを１枚引いてもよい。")
SPELL_TEXT = ("S・トリガー\n"
              "相手のマナゾーンのカードが自分のより多ければ、"
              "自分の山札の上から２枚をマナゾーンに置く。")
FULL_TEXT = (f"煌メク聖晶 弩楼: {CREATURE_TEXT}／"
             f"ビスティック・マース: {SPELL_TEXT}")

COUNT_EXPR = {"count": {"bundle_of": {"zone": "shield", "owner": "you"},
                        "filter": {"face_up": True}}}

FACES = [
    {"name": "煌メク聖晶 弩楼",
     "types": ["creature"], "civs": ["light"], "cost": 9,
     "power": 11500, "races": ["メタリカ", "サバキスト"],
     "keywords": ["blocker", "double_breaker"],
     "abilities": [
         {"kind": "trigger",
          "when": {"event": "move", "to": "bz", "subject": "self"},
          "effect": [{"op": "repeat", "times": COUNT_EXPR,
                      "body": [{"op": "may", "body": [
                          {"op": "draw", "count": 1}]}]}]}]},
    {"name": "ビスティック・マース",
     "types": ["spell"], "civs": ["light"], "cost": 4,
     "keywords": ["s_trigger"],
     "spell": [
         {"op": "if",
          "cond": {"cmp": [{"count": {"zone": "mana", "owner": "opp"}},
                           ">",
                           {"count": {"zone": "mana", "owner": "you"}}]},
          "then": [{"op": "mana_put",
                    "select": {"zone": "deck", "owner": "you",
                               "from_top": 2}}]}]},
]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1231")
    assert c["name"] == NAME
    assert c["mana"] == 1
    assert c["text"] == FULL_TEXT
    assert c["faces"] == FACES
    d = parse_card(copy.deepcopy(c), TABLES)
    f0, f1 = d.faces
    assert f0.name == "煌メク聖晶 弩楼"
    assert f0.types == ["creature"] and f0.civs == ["light"]
    assert f0.cost == 9 and f0.power == 11500
    assert f0.races == ["メタリカ", "サバキスト"]
    assert {"kind": "static", "affects": "self",
            "mod": {"allow": ["block"]},
            "keyword": "blocker"} in f0.abilities
    assert {"kind": "static", "affects": "self",
            "mod": {"breaks": 2},
            "keyword": "double_breaker"} in f0.abilities
    assert FACES[0]["abilities"][0] in f0.abilities
    assert f1.name == "ビスティック・マース"
    assert f1.types == ["spell"] and f1.cost == 4
    # mana_put は parse で move {to: mana, reason: put} に正規化される
    assert f1.spell == [
        {"op": "if",
         "cond": {"cmp": [{"count": {"zone": "mana", "owner": "opp"}},
                          ">",
                          {"count": {"zone": "mana", "owner": "you"}}]},
         "then": [{"op": "move",
                   "select": {"zone": "deck", "owner": "you",
                              "from_top": 2},
                   "to": "mana", "reason": "put"}]}]


def test_form_def_errors():
    base = {"id": "X441", "name": NAME, "mana": 1, "text": "x",
            "faces": copy.deepcopy(FACES)}
    parse_card(copy.deepcopy(base), TABLES)
    # フィルタの未知キー
    bad = copy.deepcopy(base)
    bad["faces"][0]["abilities"][0]["effect"][0]["times"] = {
        "count": {"bundle_of": {"zone": "shield", "owner": "you"},
                  "filter": {"face_ups": True}}}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # bundle_of 内側セレクタの未知ゾーン
    bad = copy.deepcopy(base)
    bad["faces"][0]["abilities"][0]["effect"][0]["times"] = {
        "count": {"bundle_of": {"zone": "shieldd", "owner": "you"},
                  "filter": {"face_up": True}}}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # 未知の op
    bad = copy.deepcopy(base)
    bad["faces"][0]["abilities"][0]["effect"][0]["op"] = "repeatt"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # cmp の未知の演算子
    bad = copy.deepcopy(base)
    bad["faces"][1]["spell"][0]["cond"]["cmp"][1] = ">>"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


# ---------- ドライバ ----------

def _keys(d):
    return [o.get("key") for o in d["options"]]


def _drive(e, on_decision, limit=800):
    for _ in range(limit):
        if e.s.result is not None:
            return "result"
        d = e.advance()
        if d is None:
            return "done"
        r = on_decision(e, d)
        if r == "stop":
            return "stopped"
        if r == "ok":
            continue
        keys = _keys(d)
        if d["kind"] in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("driver limit reached")


def _arrange_face_up(e):
    """自分のシールド5枚を: 束a（トップ表向き＋下に表向き）
    / 束c（トップ裏向き＋下に表向き）/ 束f（裏向きのみ）に
    組み替える。表向きカードは3枚、表向きを含む束は2つ。"""
    s = e.s
    a, b, c, d, f = list(e.zlist("shield", 0))
    lst = e.zlist("shield", 0)
    for u in (b, d):
        lst.remove(u)
    s.cards[a].under = [b]
    s.cards[b].top_of = a
    s.cards[c].under = [d]
    s.cards[d].top_of = c
    for cid in (a, b, d):
        s.cards[cid].face_up = True
    return e


def test_count_discrimination(rules):
    """数えの判別: 表向きカードは3枚（覆われた下の
    表向きも数える）で、束単位の bundles（2）とは
    一致しない。相手の表向きは数えない。"""
    e = scenario.build(rules, {
        "p0": {"shield": ["T001"] * 5},
        "p1": {"shield": ["T001"] * 5},
        "filler": "T002", "seed": 1, "deck_size": 20})
    _arrange_face_up(e)
    env = {"you": 0}
    assert e.eval_expr(COUNT_EXPR, env) == 3
    assert e.eval_expr({"bundles": {"owner": "you", "face_up": True}},
                       env) == 2
    # 相手のシールドを表向きにしても自分の数えは不変
    oc = e.zlist("shield", 1)[0]
    e.s.cards[oc].face_up = True
    assert e.eval_expr(COUNT_EXPR, env) == 3
    assert e.eval_expr(
        {"count": {"bundle_of": {"zone": "shield", "owner": "opp"},
                   "filter": {"face_up": True}}}, env) == 1


# ---------- クリーチャー面: 出た時のドロー ----------

def _summon_1231(rules, answers, arrange=True):
    """T1231 を召喚し、CIP の may（1枚ごと）に answers の
    列で答える。戻り値: (engine, may の提示回数)。観測点は
    相手ターンのチャージ。"""
    e = scenario.build(rules, {
        "p0": {"hand": ["T1231"], "mana": ["T339"] * 9,
               "shield": ["T001"] * 5},
        "p1": {},
        "filler": "T002", "seed": 1, "deck_size": 20})
    if arrange:
        _arrange_face_up(e)
    state = {"played": False, "mays": 0}
    queue = list(answers)

    def on_dec(e, d):
        keys = _keys(d)
        if not state["played"] and d["kind"] == "main" \
                and d.get("player") == 0 \
                and "play:T1231:0" in keys:
            state["played"] = True
            e.answer([keys.index("play:T1231:0")])
            return "ok"
        if state["played"] and d["kind"] == "pay_mana":
            e.answer([0])
            return "ok"
        if state["played"] and d["kind"] == "yes_no" \
                and d.get("player") == 0:
            state["mays"] += 1
            ans = queue.pop(0) if queue else "no"
            e.answer([keys.index(ans)])
            return "ok"
        if state["played"] and d["kind"] == "charge" \
                and d.get("player") == 1:
            return "stop"
        return None

    _drive(e, on_dec)
    return e, state["mays"]


def test_cip_draws_for_each_face_up_card(rules):
    """表向き3枚 → may が3回提示され、全部 yes で
    3枚引く（覆われた下の表向きも数える）。"""
    e, mays = _summon_1231(rules, ["yes", "yes", "yes"])
    assert mays == 3
    assert len(e.zlist("hand", 0)) == 3
    assert len(e.zlist("bz", 0)) == 1


def test_cip_draw_is_optional_per_card(rules):
    """1枚ごとに任意: yes / no / yes で2枚だけ引く。"""
    e, mays = _summon_1231(rules, ["yes", "no", "yes"])
    assert mays == 3
    assert len(e.zlist("hand", 0)) == 2


def test_cip_no_face_up_no_draw(rules):
    """表向きが無ければ may は提示されず引かない。"""
    e, mays = _summon_1231(rules, [], arrange=False)
    assert mays == 0
    assert len(e.zlist("hand", 0)) == 0
    assert len(e.zlist("bz", 0)) == 1


# ---------- 呪文面: マナ比較 ----------

def _cast_spell_face(rules, own_mana, opp_mana):
    """T1231 の呪文面を唱える。戻り値: engine。観測点は
    相手ターンのチャージ。"""
    e = scenario.build(rules, {
        "p0": {"hand": ["T1231"], "mana": ["T339"] * own_mana},
        "p1": {"mana": ["T001"] * opp_mana},
        "filler": "T002", "seed": 1, "deck_size": 20})
    state = {"played": False}

    def on_dec(e, d):
        keys = _keys(d)
        if not state["played"] and d["kind"] == "main" \
                and d.get("player") == 0 \
                and "play:T1231:1" in keys:
            state["played"] = True
            e.answer([keys.index("play:T1231:1")])
            return "ok"
        if state["played"] and d["kind"] == "pay_mana":
            e.answer([0])
            return "ok"
        if state["played"] and d["kind"] == "charge" \
                and d.get("player") == 1:
            return "stop"
        return None

    _drive(e, on_dec)
    return e


def test_spell_face_puts_two_mana_when_opponent_has_more(rules):
    """相手マナ5 > 自分4 → 山札の上から2枚が
    アンタップでマナゾーンに置かれ、呪文は墓地へ。"""
    e = _cast_spell_face(rules, own_mana=4, opp_mana=5)
    mana = e.zlist("mana", 0)
    assert len(mana) == 6
    untapped = [c for c in mana if not e.s.cards[c].tapped]
    assert len(untapped) == 2
    assert [e.s.cards[c].defn for c in e.zlist("graveyard", 0)] == ["T1231"]


def test_spell_face_does_nothing_when_not_behind(rules):
    """相手マナ5 = 自分5 → 何も置かれない。"""
    e = _cast_spell_face(rules, own_mana=5, opp_mana=5)
    assert len(e.zlist("mana", 0)) == 5
    assert [e.s.cards[c].defn for c in e.zlist("graveyard", 0)] == ["T1231"]
