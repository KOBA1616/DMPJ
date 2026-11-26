"""語彙パイロット第403弾: cast_limit_once_per_turn（ドリフト）。

センサス（rejects 1,930件を取り直し）: pure 1,782件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜402弾）は再提案しない。
graveyard_replacement の残り1件（dm25ex2-cho021）、
battle_opponent_reference の残り1件（dmr01-049）、
untap_restriction の残り2件（dm26rp1-td004 /
dmx15-011）は先行弾の評価を覆す根拠が無く再提案
しない。destroyed_this_turn_condition と
count_cards_drawn_this_turn は次点のまま残す。
enters_tapped_rule（dmex11-005、静的効果3件）は
後続候補のまま。本弾で個別に評価して見送った候補:
attack_limit_once_per_turn（pure 1、dm23bd7-004。
条項自体は回数型 deny の同型だが、ツインパクトの
partial が素で呪文面の構築から要り本弾より重い）、
attack_count_this_turn_condition（pure 1、
dm25ex3-014。第387弾の turn_count attack で条件部は
数えられるが、効果は「自分のターン終わりに墓地から
タップして出す」で墓地を発生源にするターン終了時
誘発＋超魂X が同居し未検証。次点のまま）、
no_untap_until_next_own_turn_start（pure 1、
dm26rp1-s002。partial に4能力構築済みで、条項は
シールド追加誘発→タップ＋ until_next_own_turn_start
の deny untap_at_start modify という合成が要り
本弾より重い）、s_trigger_lock（pure 1、
dm26ex3-013。「このクリーチャーがタップしていれば」
という発生源自身のタップ状態を条件にする static if
の形が未確立）、mana_enters_untapped（pure 1、
dm25-028。多色マナ配置（405.1）の置換で、配置時の
タップを打ち消す発生源側フックが未確立）。
範囲内・最小の **cast_limit_once_per_turn
（pure 1件）** を選定した。なおこの gap は multi
2件（一音の妖精 dm26ex2-pr006 / dm26ex4-cho031、
opponent_creature_entry_limit_once_per_turn との
複合）にも現れるが、そちらは本弾の対象外で、
本弾の登録後も2件とも残る。

対象は dmex03-g02 ゴールデン・ザ・ジョニー
（無色のクリーチャー / コスト7 / パワー10000 /
種族 ジョーカーズ）。partial は骨格完備＋
keywords [speed_attacker, double_breaker]＋
マスター・ブラスターの攻撃時誘発が構築済みで、
未解決は unsupported の cast_limit_once_per_turn
1件だけ。partial の text は公式全文と一致するため
**補完なし**。alias は dmex01-076 / promoy16-063
の2件で、いずれも rejects に独自行は無く、identity
実測で canon_id は対象・全 alias とも dmex03-g02、
aliases_for = 2件。

条項「相手は、各ターンに一度しか呪文を唱えられない」
の確立形は static {affects: {zone: hand, owner: opp,
filter: {types: [spell]}}, mod: {deny: [{action:
cast, max_per_turn: 1}]}} の1件（追加語彙なし）:
- 回数型 deny は第182弾の語彙。permits は deny 項目の
  max_per_turn を見て、そのターンに hist:<count>:
  <そのカードのコントローラ> が上限以上なら禁止を
  当てる。count 省略時は action 名が履歴 kind に
  なり、hist:cast は詠唱レコードから集約される
  （events._record_history）。第182弾では modify
  （duration つき）で登録済みで、本弾はそれを常在型
  static に載せるだけのドリフト。
- deny cast の範囲付け（相手の手札の呪文への
  static）は、ラビリンス登録カード（ラウンド241、
  affects {zone: hand, owner: opp, filter: {types:
  [spell], cost_le: 5}}＋deny cast）の作法と同型。
  手札以外のゾーンからの詠唱には deny が載らない
  のも、登録済み deny cast 形すべてに共通する
  エンジンの作法（本弾固有の制限ではない）。
- partial の注記「回数制限つき deny が無い」は
  第182弾より前の陳腐化。
- **実測で固定した S・トリガーとの関係**: S・トリガー
  詠唱も詠唱レコードを通るため hist:cast に数えられ、
  実行段階で permits(cast) が効く。W・ブレイカーで
  割れた S・トリガー呪文2枚を両方宣言すると、1枚目は
  解決し、2枚目は上限に達して実行されず手札に残る
  （対照: 発生源が無ければ2枚とも解決する）。公式
  でも S・トリガーで唱えることは「呪文を唱える」
  に含まれるため、この読みで文面と一致する。
- max_per_turn / count は defs と schema.py の
  両側に定義済みを確認（第408ラウンドの教訓）。
  登録ブロッカーの確認（第375弾の教訓）:
  rule_convert.split（対象行）は ([speed_attacker,
  double_breaker], 条項テキスト, []) を返し、
  part[2] の定型所有は空＝ブロッカー無し（実測）。

確立形: abilities = [partial 構築済みの攻撃時誘発，
上記 static] の2件、keywords = [speed_attacker,
double_breaker]。

proto T1170（dmex03-g02 型）。判別役は既存 proto
を流用: T003（相手の詠唱役＝水コスト2ドロー呪文）/
T001（マナ役・相手の召喚対照役）/ T408（ジョーカーズ
マナ役＝マスター・ブラスター判別）/ T960・T961
（相手の S・トリガー呪文役）/ T005（S・トリガー
対照の攻撃役＝SA＋W・ブレイカー）。

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
           "when": {"event": "attack", "subject": "self"},
           "if": {"cmp": [{"sum": [
               {"count": {"zone": "bz", "owner": "you",
                          "filter": {"race_has": "ジョーカーズ"}}},
               {"count": {"zone": "mana", "owner": "you",
                          "filter": {"race_has": "ジョーカーズ"}}}]},
               ">=", 4]},
           "effect": [
               {"op": "choose",
                "select": {"zone": "bz", "owner": "opp", "count": 1},
                "as": "target"},
               {"op": "move", "select": {"ref": "target"},
                "to": "deck", "position": "bottom", "reason": "put"}]}
STATIC = {"kind": "static",
          "affects": {"zone": "hand", "owner": "opp",
                      "filter": {"types": ["spell"]}},
          "mod": {"deny": [{"action": "cast", "max_per_turn": 1}]}}
FORM = [TRIGGER, STATIC]
FULL_TEXT = ("スピードアタッカー　W・ブレイカー\n"
             "マスター・ブラスター（このクリーチャーが攻撃する時、"
             "バトルゾーンまたはマナゾーンに自分のジョーカーズが"
             "合計４枚以上あれば、バトルゾーンにある相手のカードを"
             "１枚選ぶ。相手はそれを自身の山札の一番下に置く）\n"
             "相手は、各ターンに一度しか呪文を唱えられない。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1170")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"]
    assert c["civs"] == ["zero"] and c["cost"] == 7
    assert c["power"] == 10000 and c["mana"] == 1
    assert c["races"] == ["ジョーカーズ"]
    assert c["keywords"] == ["speed_attacker", "double_breaker"]
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.abilities == rules.cards["T1170"].abilities
    for tid in ("T003", "T001", "T408", "T960", "T961", "T005"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX403", "name": "x",
                    "types": ["creature"], "civs": ["zero"],
                    "cost": 7, "power": 10000,
                    "races": ["ジョーカーズ"], "mana": 1,
                    "keywords": ["speed_attacker", "double_breaker"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    p = parse_card(proto_card("T1170"), TABLES)
    assert d.abilities == p.abilities


def _bad(mod):
    return {"id": "TX403", "name": "x",
            "types": ["creature"], "civs": ["zero"],
            "cost": 7, "power": 10000, "races": ["ジョーカーズ"],
            "mana": 1, "keywords": ["speed_attacker", "double_breaker"],
            "abilities": [{"kind": "static",
                           "affects": {"zone": "hand", "owner": "opp",
                                       "filter": {"types": ["spell"]}},
                           "mod": mod}]}


def test_invalid_forms():
    # max_per_turn は 1 以上の整数でなければならない
    with pytest.raises(DefError):
        parse_card(_bad({"deny": [{"action": "cast",
                                   "max_per_turn": 0}]}), TABLES)
    with pytest.raises(DefError):
        parse_card(_bad({"deny": [{"action": "cast",
                                   "max_per_turn": "1"}]}), TABLES)
    # count は履歴 kind でなければならない
    with pytest.raises(DefError):
        parse_card(_bad({"deny": [{"action": "cast", "max_per_turn": 1,
                                   "count": "bogus"}]}), TABLES)
    # deny 項目の未知キー
    with pytest.raises(DefError):
        parse_card(_bad({"deny": [{"action": "cast", "max_per_turn": 1,
                                   "bogus": 1}]}), TABLES)
    # 未知の action
    with pytest.raises(DefError):
        parse_card(_bad({"deny": [{"action": "bogus_action",
                                   "max_per_turn": 1}]}), TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _cid(e, p, defn, zone):
    return next(c for c in e.zlist(zone, p)
                if e.cdef(c).id == defn
                and e.s.cards[c].controller == p)


def _drive(e, plays0=(), plays1=(), attacker=None, attacker_player=0,
           pick=None, strigger_all=False, stop=None, limit=1200):
    """汎用ドライバ（第402弾と同型に S・トリガー全宣言を追加）。"""
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
        elif kind == "declare_strigger":
            e.answer(list(range(len(keys))) if strigger_all else [])
        elif pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("limit reached")


def _cast_first_spell(e):
    """相手（p1）が手札の T003 を1枚唱えて墓地に置かれるまで進める。"""
    _drive(e, plays1=["play:T003"],
           stop=lambda: "T003" in _defns(e, "graveyard", 1))


def _until_main(e, player, limit=600):
    """player のメイン決定を掴んで（答えずに）返す。
    want を先に見るため、同一ターンのメインを取りこぼさない
    （第182弾の _drive と同方式）。(decision, keys) を返す。"""
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d["player"] == player:
            return d, keys
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] in ("choose_cards", "choose_shields"):
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")] if "no" in keys else [0])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("main never came")


def _cast_one_from_main(e, key="play:T003"):
    """現在の p1 メインで key を1回実行し、同じターンの
    次の p1 メイン決定を掴んで返す。"""
    d, keys = _until_main(e, 1)
    assert key in keys
    turn = e.s.turn
    e.answer([keys.index(key)])
    d, keys = _until_main(e, 1)
    assert e.s.turn == turn                      # 同一ターン内
    return d, keys


def test_second_cast_denied_same_turn(rules):
    """実挙動: 発生源がいる間、相手は1ターンに呪文を
    1枚しか唱えられない。1枚目は解決し、2枚目は
    permits が False でメインの選択肢にも出ない。"""
    e = _build(rules, {"bz": ["T1170"]},
               {"hand": ["T003", "T003"],
                "mana": ["T003", "T003", "T003", "T001", "T001", "T001"]})
    first = _cid(e, 1, "T003", "hand")
    assert e.permits(first, "cast")              # まだ0枚: 可
    d, keys = _cast_one_from_main(e)
    assert "T003" in _defns(e, "graveyard", 1)   # 1枚目は解決した
    assert e.s.turn_counters.get("hist:cast:1") == 1
    rest = [c for c in e.zlist("hand", 1)
            if e.cdef(c).id == "T003"]
    assert len(rest) == 1
    assert not e.permits(rest[0], "cast")        # 1枚唱えた: 不可
    assert "play:T003" not in keys               # 選択肢にも出ない


def test_two_casts_without_source(rules):
    """対照: 発生源が無ければ、相手は同じターンに
    呪文を2枚唱えられる。"""
    e = _build(rules, {},
               {"hand": ["T003", "T003"],
                "mana": ["T003", "T003", "T003", "T001", "T001", "T001"]})
    d, keys = _cast_one_from_main(e)
    rest = [c for c in e.zlist("hand", 1)
            if e.cdef(c).id == "T003"]
    assert len(rest) == 1
    assert e.permits(rest[0], "cast")
    assert "play:T003" in keys                   # 同一ターンで2枚目可
    e.answer([keys.index("play:T003")])
    _drive(e, stop=lambda: _defns(e, "graveyard", 1).count("T003") >= 2)
    assert _defns(e, "graveyard", 1).count("T003") == 2


def test_limit_resets_next_turn(rules):
    """実挙動（ターン判別）: 制限はターンごとに
    リセットされる。次の自分のターンでは相手は
    再び呪文を1枚唱えられる（そして再び2枚目は不可）。"""
    e = _build(rules, {"bz": ["T1170"]},
               {"hand": ["T003", "T003"],
                "mana": ["T003", "T001", "T001", "T001", "T001"]})
    d, keys = _cast_one_from_main(e)
    rest = [c for c in e.zlist("hand", 1)
            if e.cdef(c).id == "T003"]
    assert not e.permits(rest[0], "cast")
    t0 = e.s.turn
    _drive(e, stop=lambda: e.s.turn >= t0 + 2)   # 相手→自分→相手
    assert e.permits(rest[0], "cast")            # リセットされた
    _drive(e, plays1=["play:T003"],
           stop=lambda: _defns(e, "graveyard", 1).count("T003") >= 2)
    assert _defns(e, "graveyard", 1).count("T003") == 2


def test_scope_owner_and_summon_unaffected(rules):
    """判別（範囲）: 制限は相手の呪文だけに及ぶ。
    発生源の持ち主の呪文と、相手のクリーチャーの
    召喚は、相手が1枚唱えた後でも妨げられない。"""
    e = _build(rules,
               {"bz": ["T1170"], "hand": ["T003"],
                "mana": ["T003", "T001"]},
               {"hand": ["T003", "T001"],
                "mana": ["T003", "T001", "T001", "T001", "T001"]})
    own_spell = _cid(e, 0, "T003", "hand")
    assert e.permits(own_spell, "cast")          # 持ち主は対象外
    _cast_first_spell(e)
    assert e.permits(own_spell, "cast")          # 唱えた後も対象外
    opp_creature = _cid(e, 1, "T001", "hand")
    assert e.permits(opp_creature, "summon")     # 召喚は制限されない


def test_strigger_casts_count_toward_limit(rules):
    """実挙動（S・トリガー判別）: W・ブレイカーで
    割れた相手の S・トリガー呪文2枚を両方宣言すると、
    1枚目は解決するが2枚目はそのターンの上限に
    達して実行されず手札に残る（S・トリガー詠唱も
    「呪文を唱える」に数えられる）。"""
    e = _build(rules, {"bz": ["T1170"]},
               {"shield": ["T960", "T961"]})
    st = _drive(e, attacker="T1170", attacker_player=0,
                strigger_all=True, stop=lambda: e.s.turn >= 3)
    assert st["attacked"]
    zones = {d: [z for z in ("shield", "hand", "graveyard")
                 if d in _defns(e, z, 1)] for d in ("T960", "T961")}
    assert zones["T961"] == ["graveyard"]        # 1枚目: 解決
    assert zones["T960"] == ["hand"]             # 2枚目: 上限で不発


def test_strigger_control_both_resolve(rules):
    """対照: 発生源が無ければ、宣言した S・トリガー
    呪文は2枚とも解決する。"""
    e = _build(rules, {"bz": ["T005"]},
               {"shield": ["T960", "T961"]})
    st = _drive(e, attacker="T005", attacker_player=0,
                strigger_all=True, stop=lambda: e.s.turn >= 3)
    assert st["attacked"]
    assert "T960" in _defns(e, "graveyard", 1)
    assert "T961" in _defns(e, "graveyard", 1)


def test_master_blaster_still_works(rules):
    """実挙動（partial 構築済み条項の保全）:
    ジョーカーズが bz＋マナ合計4枚以上で攻撃すると、
    マスター・ブラスターが相手のカードを山札の
    一番下に置く。合計3枚では発火しない。"""
    e = _build(rules,
               {"bz": ["T1170"], "mana": ["T408", "T408", "T408"]},
               {"bz": ["T001"]})
    st = _drive(e, attacker="T1170", attacker_player=0,
                pick="bz:T001", stop=lambda: e.s.turn >= 2)
    assert st["attacked"]
    assert "T001" not in _defns(e, "bz", 1)
    assert "T001" in _defns(e, "deck", 1)        # 山札へ（下）
    # 対照: 合計3枚（マナ2枚）では発火しない
    e = _build(rules,
               {"bz": ["T1170"], "mana": ["T408", "T408"]},
               {"bz": ["T001"]})
    st = _drive(e, attacker="T1170", attacker_player=0,
                pick="bz:T001", stop=lambda: e.s.turn >= 2)
    assert st["attacked"]
    assert "T001" in _defns(e, "bz", 1)
