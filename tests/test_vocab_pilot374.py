"""語彙パイロット第374弾: global_s_trigger_lock（ドリフト）。

センサス（rejects 1,959件を取り直し）: pure 1,811件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜373弾）は再提案しない。本弾で個別に
評価して見送った候補: end_of_attack_effect（pure 1、
dm25ex2-094。攻撃／ブロック両誘発＋タマシード条件＋
partial に無いデモニオ軽減の補完が要り本弾の最小では
ない）、s_trigger_lock（pure 1、dm26ex3-013。タップ
状態条件と「可能ならこのクリーチャーを攻撃する」の
未組立て条項が残る）、disable_s_trigger_rest_of_turn
（pure 1、dm23ex2-chog008。攻撃誘発からのターン全体
抑制の付与形が無く、シンパシーも未組立て）、
cannot_lose_game_grant（pure 1、dm23bd4-016。バトル
勝利誘発＋次の自分のターン開始までの敗北回避付与が
要る）。範囲内・未評価で最小の global_s_trigger_lock
（pure 1件、multi にも現れない）を選定した。

対象は pure 1件すべて: dm23rp1-t2 石像男（闇 /
コスト6 / パワー5000 / ヘドリアン）。partial は骨格
（abilities・keywords ともに無し）で、未解決は
unsupported の global_s_trigger_lock 1件だけ。
単面カードで未検証の面は無く、欠けた要素も無い
（補完なし）。条項「自分のクリーチャーで、すべての
文明が揃っていれば、相手は自身の「S・トリガー」を
使えない」はすべて確立済みの部品で表せる
（追加語彙なし）:

- 「すべての文明が揃っていれば」は第317弾の確立
  イディオム（登録先例 dmx16-064・dm26sd1-b005 形C）:
  {all: [cmp [{count: {zone, owner: you, filter}}, ">=", 1]
  ×5文明]}。本カードは「自分のクリーチャーで」の
  ため zone: bz・filter {types: [creature], civs: [文明]}
  で数える（第358弾で civ_all_present（dmex08-252）を
  見送った理由は G・ゼロと破壊置換の併記であり、条件部
  自体は形Cの bz 版で書けることが同弾で確認済み。
  本カードは本条項のみで他機構が残らない）。
  多色クリーチャーは各文明を満たす（filter civs の
  通常の意味論。本弾で判別）。
- 「相手は自身の「S・トリガー」を使えない」は
  第369弾・登録先例 dm04-022 の deny 形の変種:
  static {affects: {zone: shield, owner: opp},
  mod: {deny: [s_trigger]}}（owner: opp の同形は
  converted に先例あり）。条件は static の if に
  置く（if つき static は converted に多数）。

確立形: abilities = [static {affects: {zone: shield,
owner: opp}, if: {all: [cmp count {zone: bz, owner:
you, filter: {types: [creature], civs: [文明]}} >= 1
×5]}, mod: {deny: [s_trigger]}}] の1件。

proto T1122（dm23rp1-t2 型）。判別役は既存 proto を
流用: T339（光・素のクリーチャー）/ T079（水・素）/
T277（火・素）/ T001（自然・素）/ T030（光水の多色
クリーチャー）/ T1107（火・パワー2000アタッカー）/
T006（S・トリガー呪文＝破壊対象パワー4000以下）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接包む
（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

CIVS5 = ["light", "water", "darkness", "fire", "nature"]


def _all_civs_creatures():
    return {"all": [{"cmp": [{"count": {"zone": "bz", "owner": "you",
                                        "filter": {"types": ["creature"],
                                                   "civs": [c]}}},
                             ">=", 1]}
                    for c in CIVS5]}


LOCK = {"kind": "static",
        "affects": {"zone": "shield", "owner": "opp"},
        "if": _all_civs_creatures(),
        "mod": {"deny": ["s_trigger"]}}
FORM = [LOCK]

# 文明カバー役: T1122 自身が闇、T339=光 / T079=水 /
# T277=火 / T001=自然（いずれも能力なしクリーチャー）
FULL = ["T1122", "T339", "T079", "T277", "T001"]
MULTI = ["T1122", "T030", "T277", "T001"]       # T030 は光水の多色
MISSING = ["T1122", "T339", "T079", "T277"]     # 自然が欠ける


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1122")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"] and c["civs"] == ["darkness"]
    assert c["cost"] == 6 and c["power"] == 5000
    assert c["races"] == ["ヘドリアン"]
    d = parse_card(copy.deepcopy(c), TABLES)
    assert LOCK in d.abilities
    for tid in ("T339", "T079", "T277", "T001", "T030", "T1107", "T006"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX374", "name": "x",
                    "types": ["creature"], "civs": ["darkness"],
                    "cost": 6, "power": 5000, "mana": 1,
                    "races": ["ヘドリアン"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert LOCK in d.abilities


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _find(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p) if e.cdef(c).id == defn)


def test_chars_deny_full_coverage(rules):
    """特性レベル: 自分のクリーチャーで全文明が揃えば
    相手のシールドにだけ deny [s_trigger] が付く
    （自分のシールドには付かない）。"""
    e = _build(rules, {"bz": FULL, "shield": ["T006"]},
               {"shield": ["T006"]})
    assert "s_trigger" in e.chars(_find(e, "shield", 1, "T006"))["deny"]
    assert "s_trigger" not in e.chars(_find(e, "shield", 0, "T006"))["deny"]


def test_chars_no_deny_missing_civ(rules):
    """特性レベル: 文明が1つ欠ければ deny は付かない。"""
    e = _build(rules, {"bz": MISSING}, {"shield": ["T006"]})
    assert "s_trigger" not in e.chars(_find(e, "shield", 1, "T006"))["deny"]


def test_chars_deny_multicolor_coverage(rules):
    """特性レベル: 多色クリーチャー（T030=光水）は
    両方の文明を満たし、全文明が揃う。"""
    e = _build(rules, {"bz": MULTI}, {"shield": ["T006"]})
    assert "s_trigger" in e.chars(_find(e, "shield", 1, "T006"))["deny"]


def _drive(e, attacker, player, break_defn=None, use_strigger=False):
    """player の attacker でプレイヤーを攻撃する。
    break_defn があればそのシールドをブレイク対象に選び、
    declare_strigger の記録と use_strigger の使用可否を
    制御する。判断ログ [(kind, player, keys), ...] を返す
    （第369弾の作法）。"""
    log = []
    attacked = False
    for _ in range(1500):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack" and d.get("player") == player and not attacked:
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit:
                attacked = True
                e.answer([hit[0]])
                continue
        if kind == "choose_shields" and break_defn:
            shields = e.zlist("shield", 1 - player)
            idx = next(i for i, c in enumerate(shields)
                       if e.cdef(c).id == break_defn)
            e.answer([idx])
            continue
        if kind == "declare_strigger":
            log.append((kind, d.get("player"), keys))
            e.answer(list(range(len(keys))) if use_strigger else [])
            continue
        if kind == "choose_cards":
            hit = [i for i, k in enumerate(keys) if attacker in k]
            if hit:
                e.answer(hit[:1])
                continue
        if kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
            continue
        e.answer(list(range(d.get("min", 0))))
        if attacked and kind == "main" and d.get("player") == player:
            break
    return log


def test_opponent_strigger_denied_full_coverage(rules):
    """実挙動: 全文明が揃っている間、相手のシールド
    （T006）がブレイクされても S・トリガーの宣言判断
    自体が出ず、カードはそのまま相手の手札に加わる
    （攻撃側は破壊されない）。"""
    e = _build(rules,
               {"bz": FULL + ["T1107"]},
               {"shield": ["T006", "T001", "T001", "T001", "T001"]})
    log = _drive(e, "T1107", 0, break_defn="T006", use_strigger=True)
    assert not [x for x in log if x[0] == "declare_strigger"]
    assert "T006" in _defns(e, "hand", 1)
    assert "T1107" in _defns(e, "bz", 0)      # 破壊されていない
    assert len(e.zlist("shield", 1)) == 4


def test_opponent_strigger_usable_missing_civ(rules):
    """対照: 文明が欠けていれば、ブレイクされた T006 は
    S・トリガーを宣言でき、使えば攻撃側（パワー2000）が
    破壊され、呪文は墓地に置かれる。"""
    e = _build(rules,
               {"bz": MISSING + ["T1107"]},
               {"shield": ["T006", "T001", "T001", "T001", "T001"]})
    log = _drive(e, "T1107", 0, break_defn="T006", use_strigger=True)
    st = [x for x in log if x[0] == "declare_strigger"]
    assert st and st[0][1] == 1 and "strigger:T006" in st[0][2]
    assert "T1107" in _defns(e, "graveyard", 0)
    assert "T006" in _defns(e, "graveyard", 1)
    assert len(e.zlist("shield", 1)) == 4
