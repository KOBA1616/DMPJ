"""語彙パイロット第440弾: bottom_deck_mill（ドリフト）。

センサス（rejects 1,892件を取り直し）: pure 1,744件
（981家族）/ multi 130件 / 空 gaps 18件。pure の大半は
範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜439弾）は原則として再提案しない。残置群
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

範囲内・最小の **bottom_deck_mill（pure 1件）の
dmx13-010 のみ** を選定した。本ファミリーは過去2度
見送られた: (1) 第359弾前後は「from_bottom が無く
新語彙が要る上、同名除外フィルタも併記」、
(2) 第387弾では「partial に破壊時条項が欠落し
評価不能」。本弾の実測で (1) の前提が両方とも
崩れたため覆して着手する（第435〜439弾と同型）。
(2) は partial の text が公式全文で両条項が読め、
欠けているのは abilities の構築だけなので、
第433・437・439弾と同型の補完（abilities）として
扱う。

対象は dmx13-010 真実の名 ハデスギル・スキル
（ゼロ / コスト8 / パワー8000 / 種族
ドラゴン・ゾンビ/アンノウン / mana 1）。partial は
骨格完備（text は公式全文、keywords
[double_breaker]）で abilities は未構築、
unsupported は本 gap 1件のみ。**補完あり:
abilities**（trigger 2件とも）。alias は無し
（identity 実測で canon は対象自身、同名の公式行は
x13 の1件のみ）。

結論はドリフト（追加語彙・エンジン・defs・スキーマ
変更なし）。形は trigger 2件:

- {when: {event: move, to: bz, subject: self},
  effect: [may [move {select: {zone: deck,
  owner: you, from_bottom: 5}, to: graveyard,
  reason: put}]]}
- {when: {event: move, from: bz, to: graveyard,
  reason: destroy, subject: self},
  effect: [may [play_free {select: {zone: graveyard,
  owner: you, filter: {types: [creature],
  colorless: true, evolution: false,
  not_name: 真実の名 ハデスギル・スキル},
  count: 1}}]]}

根拠: 山札の下からのミル move {select:
{from_bottom: N}, to: graveyard, reason: put} は
第287弾の確立形（登録先例 dmx13-015 形E・
dm26sd1-n006。count を書かなければ下から N 枚の
窓全体が候補になる）。破壊時誘発の when は確立形。
「《〜》以外の、進化ではない無色クリーチャー」の
フィルタは登録済み dmd19-006 の may [play_free
{filter: {types: [creature], evolution: false,
not_name: 自身の名}, count: 1}] と登録済み
dmx13-015 形Eの filter {colorless: true,
evolution: false}（同一文面の受け方）の組み合わせ。
公式境界: ミルの may は条項全体に掛かり、山札が
5枚未満なら残り全部を置く。破壊時誘発は
reason: destroy 限定で、バウンスでは誘発しない。
同名除外は自分のコピー全てに及ぶ（not_name は
名前照合）。colorless は civs == [] または [zero]。

proto T1230（dmx13-010 型）。判別役は T423
（ゼロ・非進化＝復活先の正例）/ T001（有色＝
colorless 判別）/ T1229（進化＝evolution 判別）/
T056（相手の破壊呪文）/ T140（相手のバウンス呪文
＝reason: destroy 判別）。

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
NAME = "真実の名 ハデスギル・スキル"
FULL_TEXT = (
    "このクリーチャーをバトルゾーンに出した時、"
    "自分の山札の一番下から５枚を墓地に置いてもよい。\n"
    "W・ブレイカー（このクリーチャーはシールドを"
    "２枚ブレイクする）\n"
    "このクリーチャーが破壊された時、"
    "《真実の名 ハデスギル・スキル》以外の、"
    "進化ではない無色クリーチャーを１体、"
    "自分の墓地からバトルゾーンに出してもよい。")

FORM = [
    {"kind": "trigger",
     "when": {"event": "move", "to": "bz", "subject": "self"},
     "effect": [{"op": "may", "body": [
         {"op": "move",
          "select": {"zone": "deck", "owner": "you",
                     "from_bottom": 5},
          "to": "graveyard", "reason": "put"}]}]},
    {"kind": "trigger",
     "when": {"event": "move", "from": "bz",
              "to": "graveyard", "reason": "destroy",
              "subject": "self"},
     "effect": [{"op": "may", "body": [
         {"op": "play_free",
          "select": {"zone": "graveyard", "owner": "you",
                     "filter": {"types": ["creature"],
                                "colorless": True,
                                "evolution": False,
                                "not_name": NAME},
                     "count": 1}}]}]},
]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1230")
    assert c["name"] == NAME
    assert c["types"] == ["creature"]
    assert c["civs"] == ["zero"]
    assert c["cost"] == 8 and c["power"] == 8000
    assert c["races"] == ["ドラゴン・ゾンビ", "アンノウン"]
    assert c["mana"] == 1
    assert c["text"] == FULL_TEXT
    assert c["keywords"] == ["double_breaker"]
    assert c["abilities"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    assert {"kind": "static", "affects": "self",
            "mod": {"breaks": 2},
            "keyword": "double_breaker"} in d.abilities
    for a in FORM:
        assert a in d.abilities


def test_form_def_errors():
    base = {"id": "X440", "name": NAME,
            "types": ["creature"], "civs": ["zero"],
            "cost": 8, "power": 8000,
            "races": ["ドラゴン・ゾンビ", "アンノウン"],
            "mana": 1, "text": "x",
            "keywords": ["double_breaker"],
            "abilities": copy.deepcopy(FORM)}
    parse_card(copy.deepcopy(base), TABLES)
    # セレクタの未知キー
    bad = copy.deepcopy(base)
    bad["abilities"][0]["effect"][0]["body"][0]["select"] = \
        {"zone": "deck", "owner": "you", "from_below": 5}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # when の reason の未知値
    bad = copy.deepcopy(base)
    bad["abilities"][1]["when"]["reason"] = "destroyy"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # フィルタの未知キー
    bad = copy.deepcopy(base)
    bad["abilities"][1]["effect"][0]["body"][0]["select"] \
        ["filter"]["colorles"] = True
    del bad["abilities"][1]["effect"][0]["body"][0] \
        ["select"]["filter"]["colorless"]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # play_free セレクタの未知ゾーン
    bad = copy.deepcopy(base)
    bad["abilities"][1]["effect"][0]["body"][0]["select"] \
        ["zone"] = "grave"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


# ---------- ドライバ ----------

def _keys(d):
    return [o.get("key") for o in d["options"]]


def _drive(e, on_decision, limit=800):
    """on_decision(e, d) の戻り値: "stop" = 止める /
    "ok" = 回答済み / None = 汎用回答。"""
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


def _cid(e, defn, player, zone):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn
                and e.s.cards[c].controller == player)


def _deck(e, player=0):
    return list(e.s.zones["deck"][player])


# ---------- セレクタ判別 ----------

def test_selector_discrimination(rules):
    """from_bottom の窓と墓地フィルタの候補計算:
    下5枚だけがミル候補になり、復活候補は
    ゼロ・非進化・同名以外の T423 だけになる。"""
    e = scenario.build(rules, {
        "p0": {"bz": ["T1230"],
               "graveyard": ["T423", "T001", "T1229", "T1230"],
               "deck": ["T827", "T003", "T828", "T827",
                        "T003", "T828", "T827"]},
        "p1": {},
        "filler": "T002", "seed": 1, "deck_size": 20})
    env = {"you": 0, "vars": {}}
    deck = _deck(e, 0)
    assert e.candidates(
        {"zone": "deck", "owner": "you", "from_bottom": 5},
        env) == deck[-5:]
    assert e.candidates(
        {"zone": "deck", "owner": "you", "from_bottom": 99},
        env) == deck
    sel = FORM[1]["effect"][0]["body"][0]["select"]
    cands = e.candidates(sel, env)
    assert [e.cdef(c).id for c in cands] == ["T423"]
    # 内訳: T001 は有色（colorless 偽）、T1229 は進化、
    # 墓地の T1230 は同名（not_name）で落ちる


# ---------- 第1条項: 下から5枚のミル ----------

def _summon_1230(rules, deck_ids, answer_yes):
    """T1230 を手札から召喚し、CIP の may に answer_yes で
    答える。戻り値: (engine, 召喚時点の山札スナップ, may が
    提示されたか)。観測点は次の相手ターンのチャージ。"""
    e = scenario.build(rules, {
        "p0": {"hand": ["T1230"], "mana": ["T423"] * 8,
               "deck": deck_ids},
        "p1": {},
        "filler": "T002", "seed": 1, "deck_size": 20,
        "deck_exact": [True, False]})
    snap = []
    state = {"played": False, "may_seen": False}

    def on_dec(e, d):
        keys = _keys(d)
        if not state["played"] and d["kind"] == "main" \
                and d.get("player") == 0 \
                and "play:T1230" in keys:
            state["played"] = True
            snap.append(_deck(e, 0))
            e.answer([keys.index("play:T1230")])
            return "ok"
        if state["played"] and d["kind"] == "pay_mana":
            e.answer([0])
            return "ok"
        if state["played"] and d["kind"] == "yes_no" \
                and d.get("player") == 0:
            state["may_seen"] = True
            e.answer([keys.index("yes" if answer_yes else "no")])
            return "ok"
        if state["played"] and d["kind"] == "charge" \
                and d.get("player") == 1:
            return "stop"
        return None

    _drive(e, on_dec)
    assert state["played"], "T1230 を召喚できなかった"
    return e, snap[0], state["may_seen"]


def test_mill_bottom_five(rules):
    """yes: 山札の下5枚が墓地に落ち、残りの並びは不変。"""
    e, snap, may_seen = _summon_1230(
        rules, ["T827", "T003", "T828", "T827", "T003",
                "T828", "T827"], answer_yes=True)
    assert may_seen
    bottom5, rest = snap[-5:], snap[:-5]
    gy = list(e.s.zones["graveyard"][0])
    assert sorted(gy) == sorted(bottom5)
    assert _deck(e, 0) == rest


def test_mill_decline(rules):
    """no: 山札はそのまま、墓地は空のまま。"""
    e, snap, may_seen = _summon_1230(
        rules, ["T827", "T003", "T828", "T827", "T003",
                "T828", "T827"], answer_yes=False)
    assert may_seen
    assert _deck(e, 0) == snap
    assert list(e.s.zones["graveyard"][0]) == []


def test_mill_short_deck(rules):
    """山札が5枚未満なら、残り全部を墓地に置く。"""
    e, snap, may_seen = _summon_1230(
        rules, ["T827", "T003", "T828", "T827"],
        answer_yes=True)
    assert may_seen
    assert len(snap) <= 5
    gy = list(e.s.zones["graveyard"][0])
    assert sorted(gy) == sorted(snap)
    assert _deck(e, 0) == []


# ---------- 第2条項: 破壊時の復活 ----------

def _destroy_1230(rules, spell, mana, answer_yes):
    """相手が spell（T056 破壊 / T140 バウンス）で場の
    T1230 を対象にする。戻り値: (engine, may が提示されたか,
    復活選択の options の defn リスト or None)。
    観測点は解決後の自分ターンのチャージ。"""
    e = scenario.build(rules, {
        "p0": {"bz": ["T1230"],
               "graveyard": ["T423", "T001", "T1229", "T1230"]},
        "p1": {"hand": [spell], "mana": mana},
        "filler": "T002", "seed": 1, "deck_size": 20})
    state = {"cast": False, "may_seen": False, "pick": None}

    def on_dec(e, d):
        keys = _keys(d)
        if not state["cast"] and d["kind"] == "main" \
                and d.get("player") == 1 \
                and f"play:{spell}" in keys:
            state["cast"] = True
            e.answer([keys.index(f"play:{spell}")])
            return "ok"
        if state["cast"] and d["kind"] == "pay_mana" \
                and d.get("player") == 1:
            e.answer([0])
            return "ok"
        if state["cast"] and d["kind"] == "choose_cards" \
                and d.get("player") == 1:
            tgt = [o for o in d["options"]
                   if o.get("cid") is not None
                   and e.cdef(o["cid"]).id == "T1230"
                   and e.s.cards[o["cid"]].zone == "bz"]
            if tgt:
                e.answer([d["options"].index(tgt[0])])
                return "ok"
        if state["cast"] and d["kind"] == "yes_no" \
                and d.get("player") == 0:
            state["may_seen"] = True
            e.answer([keys.index("yes" if answer_yes else "no")])
            return "ok"
        if state["cast"] and d["kind"] == "choose_cards" \
                and d.get("player") == 0:
            state["pick"] = [e.cdef(o["cid"]).id
                              for o in d["options"]
                              if o.get("cid") is not None]
            e.answer([0])
            return "ok"
        if state["cast"] and d["kind"] == "charge" \
                and d.get("player") == 0:
            return "stop"
        return None

    _drive(e, on_dec)
    assert state["cast"], f"{spell} を唱えられなかった"
    return e, state["may_seen"], state["pick"]


def test_destroy_revives_colorless(rules):
    """破壊された時、墓地のゼロ・非進化・同名以外
    （T423 だけが候補）をバトルゾーンに出せる。"""
    e, may_seen, pick = _destroy_1230(
        rules, "T056", ["T082"] * 3, answer_yes=True)
    assert may_seen
    # 候補は T423 のみ（セレクタ判別で実測済み）。候補が
    # 1体だけだと選択決定は自動化されて提示されない
    # （第437弾の実測）ため、提示された場合だけ一致を見る
    assert pick in (None, ["T423"])
    t423 = _cid(e, "T423", 0, "bz")
    assert e.s.cards[t423].controller == 0
    # 破壊された T1230 本体は墓地にいる
    assert any(e.cdef(c).id == "T1230"
               for c in e.zlist("graveyard", 0))
    # 落ちた候補は墓地に残る
    gy_defns = sorted(e.cdef(c).id
                      for c in e.zlist("graveyard", 0))
    assert gy_defns == ["T001", "T1229", "T1230", "T1230"]


def test_destroy_decline(rules):
    """may を断れば何も出ない。"""
    e, may_seen, pick = _destroy_1230(
        rules, "T056", ["T082"] * 3, answer_yes=False)
    assert may_seen
    assert pick is None
    assert not any(e.cdef(c).id == "T423"
                   for c in e.zlist("bz", 0))
    assert any(e.cdef(c).id == "T423"
               for c in e.zlist("graveyard", 0))


def test_bounce_does_not_trigger(rules):
    """バウンス（reason: destroy でない）では誘発しない。"""
    e, may_seen, pick = _destroy_1230(
        rules, "T140", ["T009"] * 3, answer_yes=True)
    assert not may_seen
    assert pick is None
    # T1230 は手札に戻り、墓地の候補は動かない
    assert any(e.cdef(c).id == "T1230"
               for c in e.zlist("hand", 0))
    assert any(e.cdef(c).id == "T423"
               for c in e.zlist("graveyard", 0))
