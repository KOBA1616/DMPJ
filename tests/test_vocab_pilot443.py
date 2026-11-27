"""語彙パイロット第443弾: no_untap_until_next_own_turn_start
（ドリフト）。

センサス（rejects 1,889件を取り直し）: pure は
1〜4件の小家族が多数で、大半は範囲外（gr_summon
147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift
4）。評価済み却下（第316〜320・355〜442弾）と残置群
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
milled_total_cost_selection（合計制約つき複数選択
＝第434弾の残置と同根）、break_count_double
（breaks 乗算 mod の新規語彙＋適用順序の設計が
要る）、draw_until_count（draw 数の算術式が要る
＋ハイパー面限定条項）、other_opponent_shield_break
（「他の各相手」は複数対戦の概念）、
battle_win_cost_reference_mana（up-to 枚数の
マナ置きが未検証＋ハイパー面条項）、
fortified_shield_unbreakable（要塞化シールド限定の
ブレイク不能は確立形に無い）。

範囲内・最小の **no_untap_until_next_own_turn_start
（pure 1件）の dm26rp1-s002 のみ** を選定した。
行の注記「語彙が無い」は陳腐化:
- 第2条項は trigger {when: {event: move,
  to: shield, subject: {owner: you}}, effect:
  [choose {select: {zone: bz, owner: opp,
  filter: {types: [creature]}, count: 1}, as: t},
  tap {select: {ref: t, count: all}},
  modify {select: {ref: t, count: all},
  mod: {deny: [untap_at_start]},
  duration: until_next_own_turn_start}]}。
  when は登録済み48件の確立形、choose の束縛は
  登録済み dmd23-006、modify＋duration は
  ジャストダイバーの登録形（dm22rp1-056）、
  deny [untap_at_start] は第439弾の確立形。
- 既存のフリーズ形 tap {no_untap_next: true} は
  「次の相手のターンのはじめ」型で、本条項の
  「次の自分のターンのはじめまで」とは相手の
  ターン中に解決した場合に食い違う（期限切れ後も
  相手のアンタップが奪われる）ため使わない。
  modify 形は st_start 冒頭で効果側のターン開始時に
  落ちるため、相手のターン開始では deny が生き、
  自分の次のターン開始で消える＝両ケースで一致。

対象は dm26rp1-s002 世界のY チャクラ・デル・フィン
（光 / コスト3 / パワー4000 / 種族 アポロニア・
ドラゴン/超化獣、mana 1）。partial は骨格完備
（text 公式全文、keywords [z_rush]、abilities
4件構築済み）で unsupported は本 gap 1件のみ。
**補完あり: abilities（第2条項の trigger）＋
hyper: true フィールド**（partial に欠落。
登録済み超化獣はすべて持ち、無いと {hyper: true}
条件が満たされない）。alias は dm26rp1-sec003
（独自行なし）。

結論はドリフト（追加語彙・エンジン・defs・
スキーマ変更なし）。公式境界: 選択＋タップは
任意でない。すでにタップしているクリーチャーにも
「アンタップしない」は付く。自分のシールドゾーンに
置かれるカードは理由を問わず対象で、このカード
自身の第1条項でも誘発する。deny は untap_at_start
のみで効果によるアンタップは妨げない。

proto T1233（dm26rp1-s002 型）。判別役は既存の
T001 / T008（相手クリーチャー役）。

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
NAME = "世界のY チャクラ・デル・フィン"
FULL_TEXT = (
    "このクリーチャーが出た時、自分の山札の上から１枚をシールド化する。\n"
    "カードが自分のシールドゾーンに置かれた時、相手のクリーチャーを１体選び、タップする。"
    "次の自分のターンのはじめまで、それはアンタップしない。\n"
    "Zラッシュ（シールドが離れたら、次の自分のターンのはじめまで、このクリーチャーのハイパーモードを解放する）")

CLAUSE2 = {"kind": "trigger",
           "when": {"event": "move", "to": "shield",
                    "subject": {"owner": "you"}},
           "effect": [
               {"op": "choose",
                "select": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"]},
                           "count": 1},
                "as": "t"},
               {"op": "tap",
                "select": {"ref": "t", "count": "all"}},
               {"op": "modify",
                "select": {"ref": "t", "count": "all"},
                "mod": {"deny": ["untap_at_start"]},
                "duration": "until_next_own_turn_start"}]}

ABILITIES = [
    {"kind": "static", "affects": "self",
     "mod": {"power": 3500}, "if": {"hyper": True}},
    {"kind": "trigger",
     "when": {"event": "move", "to": "bz", "subject": "self"},
     "effect": [{"op": "move",
                 "select": {"zone": "deck", "owner": "you",
                            "count": 1, "from_top": 1},
                 "to": "shield", "reason": "charge"}]},
    CLAUSE2,
    {"kind": "static", "affects": "self",
     "mod": {"grant": ["blocker", "double_breaker"]},
     "if": {"hyper": True}},
    {"kind": "static",
     "affects": {"zone": "hand", "owner": "opp",
                 "filter": {"types": ["spell"], "cost_le": 5}},
     "mod": {"deny": ["cast"]}, "if": {"hyper": True}},
]

FORM = {"name": NAME, "types": ["creature"],
        "civs": ["light"], "cost": 3, "power": 4000,
        "races": ["アポロニア・ドラゴン", "超化獣"],
        "mana": 1, "keywords": ["z_rush"], "hyper": True,
        "text": FULL_TEXT, "abilities": ABILITIES}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1233")
    for k, v in FORM.items():
        assert c[k] == v, k
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.name == NAME and d.power == 4000
    # parse は FORM の abilities をそのまま保持する
    assert d.abilities == ABILITIES


def test_form_def_errors():
    base = {"id": "X443", **copy.deepcopy(FORM)}
    parse_card(copy.deepcopy(base), TABLES)
    # duration の不正値
    bad = copy.deepcopy(base)
    bad["abilities"][2]["effect"][2]["duration"] = \
        "until_next_own_turn_strt"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # deny の未知アクション
    bad = copy.deepcopy(base)
    bad["abilities"][2]["effect"][2]["mod"] = \
        {"deny": ["untap_at_strt"]}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # 未知の op
    bad = copy.deepcopy(base)
    bad["abilities"][2]["effect"][0]["op"] = "choosee"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # when の未知イベント
    bad = copy.deepcopy(base)
    bad["abilities"][2]["when"]["event"] = "movee"
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


def _drive(e, choose_target=None, after=None,
           stop=None, limit=1200):
    """choose_target: 第2条項の choose 判断（player 0 の
    choose_cards）で選ぶ cid。after(e, d, st) は各判断に
    答えた後に呼ばれる（ev_task 注入用。注入はターン
    開始処理より後に置くこと: 開始ステップより前に
    解決させると、生成した継続的効果がそのターン開始の
    期限切れ処理に巻き込まれる＝実ゲームでは起きない
    人工物）。stop(e, d, st) が True を返した判断は
    答えずに止める。"""
    st = {"charges": {0: 0, 1: 0}, "chose": 0}
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if d["kind"] == "charge":
            st["charges"][d["player"]] += 1
        if stop is not None and stop(e, d, st):
            return st
        if d["kind"] == "choose_cards" \
                and d.get("player") == 0 \
                and choose_target is not None:
            idx = next(i for i, o in enumerate(d["options"])
                       if o.get("cid") == choose_target)
            e.answer([idx])
            st["chose"] += 1
        else:
            _answer_default(e, d)
        if after is not None:
            after(e, d, st)
    raise AssertionError("driver limit reached")


def _inject_once(fn, kind, player):
    """kind/player の判断に答えた直後に fn(e) を1回だけ
    実行する after フック。"""
    state = {"done": False}

    def after(e, d, st):
        if not state["done"] and d["kind"] == kind \
                and d.get("player") == player:
            state["done"] = True
            fn(e)
    after.state = state
    return after


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn
                and e.s.cards[c].controller == p)


def _shieldize_inject(e, player=0):
    """player の山札の上1枚をシールドゾーンへ置く move
    イベントを注入する（第128弾の ev_task 作法）。
    第2条項は理由を問わないため reason は put。"""
    top = e.zlist("deck", player)[0]
    e._push(e.ev_task([{"ev": "move",
                        "subject": e.s.ref(top),
                        "to": "shield", "reason": "put"}]))


def _at_charge(player, turn):
    """player の turn ターン目の charge 判断（そのターンの
    アンタップステップ処理後）で止める。ターンは絶対番号
    （1＝先攻の最初のターン）で数える: _drive を分割して
    呼んでも数え直しにならない。"""
    def stop(e, d, st):
        return d["kind"] == "charge" \
            and d.get("player") == player \
            and e.s.turn == turn
    return stop


# ---------- 第2条項: 自分のターン中に解決 ----------

def test_clause2_flow_resolved_on_own_turn(rules):
    """自分のターン中にシールド化 → 相手の T001 を選んで
    タップ＋アンタップ否定。相手ターン1のはじめには
    アンタップせず（deny が生きている）、自分の
    ターン2のはじめで期限が切れ、相手ターン2のはじめに
    通常どおりアンタップする。選ばなかった T008 は
    無影響。"""
    e = _build(rules, {"bz": ["T1233"], "hand": ["T002", "T002"]},
               {"bz": ["T001", "T008"]})
    tgt = _cid(e, 1, "T001")
    other = _cid(e, 1, "T008")
    inj = _inject_once(lambda eng: _shieldize_inject(eng, 0),
                       "charge", 0)
    # 相手ターン1の charge（アンタップステップ後）まで
    st = _drive(e, choose_target=tgt, after=inj,
                stop=_at_charge(1, 2))
    assert inj.state["done"]
    assert st["chose"] == 1
    assert e.s.cards[tgt].tapped
    assert e.permits(tgt, "untap_at_start") is False
    assert not e.s.cards[other].tapped
    assert e.permits(other, "untap_at_start") is True
    # 自分ターン2の charge まで: 期限が切れている
    st = _drive(e, choose_target=tgt, stop=_at_charge(0, 3))
    assert e.permits(tgt, "untap_at_start") is True
    assert e.s.cards[tgt].tapped  # 相手のはじめまでは倒れたまま
    # 相手ターン2の charge まで: 通常どおりアンタップ
    st = _drive(e, choose_target=tgt, stop=_at_charge(1, 4))
    assert not e.s.cards[tgt].tapped


def test_clause2_flow_resolved_on_opponent_turn(rules):
    """相手のターン中にシールド化 → 第2条項が解決しても、
    期限は「次の自分のターンのはじめまで」なので、
    自分のターン開始で deny は消え、相手は次の自分の
    ターンのはじめに通常どおりアンタップする。
    フリーズ形（no_untap_next）なら奪われるアンタップが
    奪われないことの判別。"""
    e = _build(rules, {"bz": ["T1233"], "hand": ["T002", "T002"]},
               {"bz": ["T001", "T008"], "hand": ["T002"],
               "mana": ["T002", "T002"]})
    tgt = _cid(e, 1, "T001")
    inj = _inject_once(lambda eng: _shieldize_inject(eng, 0),
                       "main", 1)

    # 自分ターン2の charge（相手ターン1を経た後）まで
    st = _drive(e, choose_target=tgt, after=inj,
                stop=_at_charge(0, 3))
    assert inj.state["done"]
    assert st["chose"] == 1
    assert e.s.cards[tgt].tapped
    # 自分のターンのはじめで期限切れ（deny は消えている）
    assert e.permits(tgt, "untap_at_start") is True
    # 相手ターン2の charge まで: 通常どおりアンタップ
    st = _drive(e, choose_target=tgt, stop=_at_charge(1, 4))
    assert not e.s.cards[tgt].tapped


def test_clause2_already_tapped_target_still_denied(rules):
    """すでにタップしているクリーチャーを選んでも
    「アンタップしない」は付く: tap は空転するが
    modify は適用され、相手ターン1のはじめに
    アンタップしない（deny がなければ起きるはず）。"""
    e = _build(rules, {"bz": ["T1233"], "hand": ["T002", "T002"]},
               {"bz": ["T001", "T008"]})
    tgt = _cid(e, 1, "T001")
    e.s.cards[tgt].tapped = True
    inj = _inject_once(lambda eng: _shieldize_inject(eng, 0),
                       "charge", 0)
    st = _drive(e, choose_target=tgt, after=inj,
                stop=_at_charge(1, 2))
    assert inj.state["done"]
    assert st["chose"] == 1
    assert e.s.cards[tgt].tapped
    assert e.permits(tgt, "untap_at_start") is False


def test_clause2_no_opponent_creature(rules):
    """相手のクリーチャーがいなければ第2条項は空転し、
    ゲームは通常どおり進む（choose は対象なし）。"""
    e = _build(rules, {"bz": ["T1233"], "hand": ["T002", "T002"]}, {"bz": []})
    inj = _inject_once(lambda eng: _shieldize_inject(eng, 0),
                       "charge", 0)
    st = _drive(e, after=inj, stop=_at_charge(1, 2))
    assert inj.state["done"]
    assert st["chose"] == 0
    assert len(e.zlist("shield", 0)) == 6


# ---------- 第1条項→第2条項の連鎖 ----------

def test_cip_shieldize_chains_into_clause2(rules):
    """T1233 が出た時、第1条項で自分の山札の上1枚が
    シールド化され、それ自体が第2条項を誘発させる:
    シールドが6枚になり、相手の T001 がタップされ
    アンタップ否定が付く（期限切れ後は通常どおり
    アンタップする）。注入は相手ターンの main 回答後
    （第442弾の教訓: 判断タスクの再開と競合しない点。
    連鎖そのものは解決するターンに依存しない）。"""
    e = _build(rules, {"hand": ["T1233"]},
               {"bz": ["T001", "T008"], "hand": ["T002"],
                "mana": ["T002", "T002"]})
    src = next(c for c in e.zlist("hand", 0)
               if e.s.cards[c].defn == "T1233")
    tgt = _cid(e, 1, "T001")

    def enter(eng):
        eng._push(eng.ev_task([{"ev": "move",
                                "subject": eng.s.ref(src),
                                "to": "bz", "reason": "summon"}]))
    inj = _inject_once(enter, "main", 1)
    # 自分ターン2（絶対ターン3）の charge まで
    st = _drive(e, choose_target=tgt, after=inj,
                stop=_at_charge(0, 3))
    assert inj.state["done"]
    assert st["chose"] == 1
    assert len(e.zlist("shield", 0)) == 6
    assert e.s.cards[tgt].tapped
    # 相手ターン2（絶対ターン4）の charge まで:
    # 期限が切れているので通常どおりアンタップする
    st = _drive(e, choose_target=tgt, stop=_at_charge(1, 4))
    assert not e.s.cards[tgt].tapped
