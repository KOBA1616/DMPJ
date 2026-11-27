"""語彙パイロット第438弾: revolution_2（ドリフト）。

センサス（rejects 1,894件を取り直し）: pure 1,746件
（982家族）/ multi 130件 / 空 gaps 18件。pure の大半は
範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜437弾）は原則として再提案しない。残置群
（graveyard_replacement 残り dm25ex2-cho021、
battle_opponent_reference 残り dmr01-049、
untap_restriction 残り2件、does_not_untap 残り
dm25ex2-031、cast_limit_once_per_turn の multi 2件、
summoning_attack_rule 残り dmex07-s01、
entered_turn_attack 残り dmbd11-d05、madness 残り
dmx26-028、after_battle_trigger 残り dmrp09-074、
s_trigger_suppression 2件＝第435弾で専用ステージ
送り確定、次点の destroyed_this_turn_condition /
count_cards_drawn_this_turn、後続候補の
distinct_civ_count、将来の新規語彙候補 first_time_tap /
turn_history_entry / played_free_condition、専用
ステージ送りの power_threshold_keyword_gain）は
覆す根拠が無く再提案しない。

範囲内・最小の **revolution_2（pure 2件）のうち
dmex06-033 のみ** を選定した。もう1件の
dm26sd1-o004 は呪文で、革命２が「手札に加える
この呪文に S・トリガーを与える」付与形＋モード
2回選択の複合＝形が異なるため残置する（ラウンド
472では reopen が両行を巻き込む見込みで差し戻し
が必要）。

対象は dmex06-033 革命目 ギョギョウ（自然 /
コスト6 / パワー8000 / 種族 ジュラシック・
コマンド・ドラゴン/革命軍 / mana 1、alias
dmr19-009）。partial は骨格（evolve_from 含む）＋
keywords [double_breaker]＋第2条項の trigger まで
構築済みで text は公式全文。**補完あり:
abilities**（革命２の static 1件のみ未構築）。

結論はドリフト（追加語彙・エンジン・defs・スキーマ
変更なし）:

- 革命２は static {affects: self, zone: hand,
  if: {cmp: [{count: {zone: shield, owner: you}},
  "<=", 2]}, mod: {cost: -5}}。条件＋軽減幅は
  登録済み dmex03-s08（if {cmp: [{count:
  {zone: shield, owner: you}}, "<=", 2]} ＋
  mod {cost: -5, cost_min: 0}、affects は手札の
  クリーチャー全般）と dmd27-008（同条件で革命軍の
  進化対象）の組み合わせで、self 形は登録済み
  dmex10-s03 / dmex15-a015（affects: self ＋
  zone: hand ＋ シールド数条件の cmp ＋
  mod {cost: -4 / -5}、cost_min なし）が先例。
  公式テキストにも下限条項は無いため cost_min は
  付けない。
- 第2条項（相手クリーチャーが出た時、その
  コスト以下の自然の進化ではないクリーチャーを
  1体、自分のマナゾーンから出してもよい）は
  partial 構築済みの trigger {when: {event: move,
  to: bz, subject: {owner: opp, filter:
  {types: [creature]}}}, effect: [choose
  {select: {ref: subject}, as: entered}, may
  [move {select: {zone: mana, owner: you,
  filter: {types: [creature], civs: [nature],
  evolution: false, cost_le: {cost_of:
  entered}}, count: 1}, to: bz, reason: put}]]}
  のまま（choose の as 束縛と cost_of は
  第388・421弾等の確立形）。

proto T1228（dmex06-033 型）。判別役は T001
（自然バニラ＝進化元・マナからの出場先）/ T428
（自然コスト3＝cost_le 判別役）/ T828（自然
コスト6・能力なし＝進化フィルタ判別役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の
作法）。支払いには文明マナが要るため、相手の
プレイ役はマナに同文明のカードを置く。
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

TRIG = {"kind": "trigger",
        "when": {"event": "move", "to": "bz",
                 "subject": {"owner": "opp",
                             "filter": {"types": ["creature"]}}},
        "effect": [{"op": "choose",
                    "select": {"ref": "subject"}, "as": "entered"},
                   {"op": "may",
                    "body": [{"op": "move",
                              "select": {"zone": "mana", "owner": "you",
                                         "filter": {
                                             "types": ["creature"],
                                             "civs": ["nature"],
                                             "evolution": False,
                                             "cost_le": {
                                                 "cost_of": "entered"}},
                                         "count": 1},
                              "to": "bz", "reason": "put"}]}]}
STATIC = {"kind": "static", "affects": "self", "zone": "hand",
          "if": {"cmp": [{"count": {"zone": "shield", "owner": "you"}},
                         "<=", 2]},
          "mod": {"cost": -5}}
FORM = [TRIG, STATIC]
FULL_TEXT = ("進化：自分の自然のクリーチャー１体の上に置く。\n"
             "W・ブレイカー\n"
             "相手のクリーチャーがバトルゾーンに出た時、"
             "そのクリーチャー以下のコストを持つ、自然の進化ではない"
             "クリーチャーを１体、自分のマナゾーンから"
             "バトルゾーンに出してもよい。\n"
             "革命２：自分のシールドが２つ以下なら、"
             "このクリーチャーの召喚コストを５少なくする。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _keys(d):
    return [o.get("key") for o in d["options"]]


def _cid(e, defn, player, zone):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn
                and e.s.cards[c].controller == player)


def _drive(e, want=None, limit=400, seen=None):
    """want(kind, keys, d) -> 答えるキーの文字列 or None。
    それ以外は pass / no_block / 最小限で流す
    （charge は pass して手札を温存する）。"""
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if seen is not None:
            seen.append((d["kind"], d.get("player"), list(keys),
                         [o.get("cid") for o in d["options"]]))
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


def test_proto_form(rules):
    card = proto_card("T1228")
    assert card["abilities"] == FORM
    assert card["text"] == FULL_TEXT
    assert card["keywords"] == ["double_breaker"]
    assert card["types"] == ["creature", "evolution"]
    assert card["evolve_from"] == {"types": ["creature"],
                                   "civs": ["nature"]}
    parsed = parse_card(card, TABLES)
    assert parsed.abilities[0] == {"kind": "static", "affects": "self",
                                   "mod": {"breaks": 2},
                                   "keyword": "double_breaker"}
    assert parsed.abilities[1] == TRIG
    assert parsed.abilities[2] == STATIC


def test_form_def_errors():
    base = {"id": "X438", "name": "x",
            "types": ["creature", "evolution"],
            "civs": ["nature"], "cost": 6, "power": 8000,
            "races": ["テスト"], "mana": 1, "text": "x",
            "keywords": ["double_breaker"],
            "evolve_from": {"types": ["creature"], "civs": ["nature"]},
            "abilities": copy.deepcopy(FORM)}
    parse_card(copy.deepcopy(base), TABLES)
    bad = copy.deepcopy(base)
    bad["abilities"][1]["if"]["cmp"][1] = "=<"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = copy.deepcopy(base)
    bad["abilities"][1]["if"]["cmp"][0]["count"]["zone"] = "shieldzz"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = copy.deepcopy(base)
    bad["abilities"][1]["mod"] = {"costzz": -5}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = copy.deepcopy(base)
    bad["abilities"][0]["when"]["event"] = "movezz"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _pay_cost(rules, p0_shields, p1_shields):
    e = scenario.build(rules, {
        "p0": {"hand": ["T1228"], "shield": p0_shields},
        "p1": {"shield": p1_shields},
        "filler": "T002", "seed": 1, "deck_size": 20})
    cid = _cid(e, "T1228", 0, "hand")
    return e.chars_ro(cid)["pay_cost"]


def test_revolution_cost_by_shield_count(rules):
    """自分のシールド2つ以下で召喚コスト -5（6→1）、
    3つ以上では軽減なし。相手のシールド数は無関係。"""
    two = ["T002", "T001"]
    three = ["T002", "T001", "T001"]
    five = ["T002", "T001", "T001", "T001", "T001"]
    assert _pay_cost(rules, two, five) == 1      # 境界: ちょうど2つ
    assert _pay_cost(rules, ["T002"], five) == 1  # 1つでも成立
    assert _pay_cost(rules, three, []) == 6       # 3つでは不成立
    assert _pay_cost(rules, five, []) == 6        # 相手0でも不成立


def test_revolution_summon_with_one_mana(rules):
    """シールド2つなら1マナで進化召喚できる。
    シールド3つでは1マナでプレイ自体が提示されない。"""
    seen = []

    def want(kind, keys, d):
        if kind == "main" and d.get("player") == 0 \
                and "play:T1228" in keys:
            return "play:T1228"
        if kind == "choose_cards" and d.get("player") == 0:
            base = [o.get("key") for o in d["options"]
                    if o.get("cid") is not None
                    and e.s.cards[o["cid"]].defn == "T001"
                    and e.s.cards[o["cid"]].zone == "bz"]
            if base:
                return base[0]
        return None

    e = scenario.build(rules, {
        "p0": {"bz": ["T001"], "hand": ["T1228"], "mana": ["T001"],
               "shield": ["T002", "T001"]},
        "p1": {"shield": ["T002", "T001"]},
        "filler": "T002", "seed": 1, "deck_size": 20})
    # 召喚が解決した時点で止める（進み続けると次のターン開始で
    # マナがアンタップしてしまうため）
    hand = _cid(e, "T1228", 0, "hand")
    for _ in range(400):
        if e.s.cards[hand].zone == "bz":
            break
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        seen.append((d["kind"], d.get("player"), list(keys),
                     [o.get("cid") for o in d["options"]]))
        k = want(d["kind"], keys, d)
        if k is not None:
            e.answer([keys.index(k)])
        elif d["kind"] in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert e.s.cards[hand].zone == "bz"
    mana = _cid(e, "T001", 0, "mana")
    assert e.s.cards[mana].tapped  # 支払った1マナはタップ状態

    # main 決定はプレイ可能なカードがある時だけ提示されるため、
    # 負例はマナ5枚（引いた filler は出せるが、未軽減の
    # コスト6には届かない）で提示自体を起こす
    seen2 = []
    e = scenario.build(rules, {
        "p0": {"bz": ["T001"], "hand": ["T1228"],
               "mana": ["T001", "T001", "T001", "T001", "T001"],
               "shield": ["T002", "T001", "T001"]},
        "p1": {"shield": ["T002", "T001"]},
        "filler": "T002", "seed": 1, "deck_size": 20})
    _drive(e, want, limit=120, seen=seen2)
    mains = [ks for kind, pl, ks, _c in seen2
             if kind == "main" and pl == 0]
    assert mains, "自分のメインが一度も来なかった"
    assert all("play:T1228" not in ks for ks in mains)
    assert e.s.cards[_cid(e, "T1228", 0, "hand")].zone == "hand"


def _watcher_build(rules, p0_mana, p1_hand, p1_mana):
    return scenario.build(rules, {
        "p0": {"bz": ["T1228"], "mana": p0_mana,
               "shield": ["T002", "T001"]},
        "p1": {"hand": p1_hand, "mana": p1_mana,
               "shield": ["T002", "T001"]},
        "filler": "T002", "seed": 1, "deck_size": 20})


def _play_and_watch(e, play_key, may_answer="yes", pick_defn=None):
    """相手が play_key をプレイするまで進め、発生源の
    may（yes_no）には may_answer で答え、choose_cards では
    pick_defn のカードを選ぶ。観測した yes_no の有無と
    choose_cards の提示 cid 群を返す。"""
    state = {"played": False, "yes_no": False, "offers": []}

    def want(kind, keys, d):
        if kind == "main" and d.get("player") == 1 \
                and play_key in keys and not state["played"]:
            state["played"] = True
            return play_key
        if kind == "yes_no" and d.get("player") == 0:
            state["yes_no"] = True
            return may_answer if may_answer in keys else None
        if kind == "choose_cards" and d.get("player") == 0:
            cids = [o.get("cid") for o in d["options"]
                    if o.get("cid") is not None]
            state["offers"].append(cids)
            if pick_defn is not None:
                hit = [o.get("key") for o in d["options"]
                       if o.get("cid") is not None
                       and e.s.cards[o["cid"]].defn == pick_defn
                       and e.s.cards[o["cid"]].zone == "mana"]
                if hit:
                    return hit[0]
        return None

    _drive(e, want, limit=300)
    return state


def test_watcher_puts_creature_from_mana(rules):
    """相手のクリーチャー（コスト3）が出た時、コスト以下の
    自然クリーチャーをマナから出せる（境界: コスト3ちょうど
    の T428 を選ぶ）。"""
    e = _watcher_build(rules, ["T001", "T428"], ["T004"],
                       ["T004", "T001", "T001"])
    st = _play_and_watch(e, "play:T004", pick_defn="T428")
    assert st["played"] and st["yes_no"]
    assert e.s.cards[_cid(e, "T428", 0, "bz")].zone == "bz"
    assert e.s.cards[_cid(e, "T001", 0, "mana")].zone == "mana"


def test_watcher_cost_le_discrimination(rules):
    """出たクリーチャーのコストが2なら、コスト3の T428 は
    選択肢に出ない（cost_le: {cost_of: entered} の判別）。"""
    e = _watcher_build(rules, ["T001", "T428"], ["T001"],
                       ["T001", "T001"])
    st = _play_and_watch(e, "play:T001", pick_defn="T001")
    assert st["played"] and st["yes_no"]
    offered = [e.s.cards[c].defn for offer in st["offers"] for c in offer]
    assert "T428" not in offered
    assert e.s.cards[_cid(e, "T001", 0, "bz")].zone == "bz"
    assert e.s.cards[_cid(e, "T428", 0, "mana")].zone == "mana"


def test_watcher_evolution_filter_discrimination(rules):
    """コスト6のクリーチャーが出ても、進化クリーチャー
    （T1228 自身）は evolution: false で選択肢に出ない。"""
    e = _watcher_build(rules, ["T1228", "T001"], ["T828"],
                       ["T001"] * 6)
    st = _play_and_watch(e, "play:T828", pick_defn="T001")
    assert st["played"] and st["yes_no"]
    offered = [e.s.cards[c].defn for offer in st["offers"] for c in offer]
    assert "T1228" not in offered
    assert e.s.cards[_cid(e, "T001", 0, "bz")].zone == "bz"
    assert e.s.cards[_cid(e, "T1228", 0, "mana")].zone == "mana"


def test_watcher_may_decline(rules):
    """may を辞退すればマナのクリーチャーは出ない。"""
    e = _watcher_build(rules, ["T001", "T428"], ["T004"],
                       ["T004", "T001", "T001"])
    st = _play_and_watch(e, "play:T004", may_answer="no")
    assert st["played"] and st["yes_no"]
    assert e.s.cards[_cid(e, "T001", 0, "mana")].zone == "mana"
    assert e.s.cards[_cid(e, "T428", 0, "mana")].zone == "mana"


def test_watcher_own_entry_no_trigger(rules):
    """自分のクリーチャーが出ても誘発しない
    （subject owner: opp の判別）。"""
    e = scenario.build(rules, {
        "p0": {"bz": ["T1228"], "hand": ["T001"],
               "mana": ["T428", "T001", "T001"],
               "shield": ["T002", "T001"]},
        "p1": {"shield": ["T002", "T001"]},
        "filler": "T002", "seed": 1, "deck_size": 20})
    seen = []

    def want(kind, keys, d):
        if kind == "main" and d.get("player") == 0 \
                and "play:T001" in keys:
            return "play:T001"
        return None

    _drive(e, want, limit=200, seen=seen)
    assert e.s.cards[_cid(e, "T001", 0, "bz")].zone == "bz"
    t428 = _cid(e, "T428", 0, "mana")
    offered = [c for kind, pl, _ks, cids in seen
               if kind == "choose_cards" and pl == 0
               for c in cids if c is not None]
    assert t428 not in offered
    assert e.s.cards[t428].zone == "mana"
