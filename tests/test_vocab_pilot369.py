"""語彙パイロット第369弾: no_shield_break（ドリフト）。

センサス（rejects 1,964件を取り直し）: pure 1,816件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜368弾）は再提案しない。本弾で個別に
評価して見送った候補: count_distinct_races（pure 1、
dm20-037。異なる種族の数を数える式が count_of に無く
新語彙が要る）、tap_all_weaker_than_chosen（pure 1、
dm22ex1-059。選んだクリーチャーのパワー未満という
動的パワー参照フィルタが要る）、
destroy_attack_target_without_battle（pure 1、
dm20-028。「バトルは行われない」の置換が要り
battle_does_not_occur 系の却下と同根）、
same_name_bounce（pure 1、dmrp04m-048。選んだ
クリーチャーと同名という動的名称参照が要る）、
leave_trigger（pure 1、dm37-045。離脱誘発に加え
公開・選択の複合で最小でない）、force_block（pure 1、
dmr09-004。ブロック強制は別機構）。set_power_to_zero
（pure 1、dm24ex2-042）は modify {power_set: 0} の
登録先例（dmrp11-zs01）と crystal_soul: 2 の登録先例が
あり表現可能と評価したが、本弾ではより小さい
no_shield_break を優先した（次弾以降の候補として残す）。
範囲内・未評価で最小の no_shield_break（pure 1件、
multi にも現れない）を選定した。

対象は pure 1件すべて: dmex03-061 夜のポンの助
（ゼロ / コスト1 / パワー820 / ジョーカーズ）。partial は
骨格（abilities・keywords ともに無し）で、未解決は
unsupported の no_shield_break 1件だけ。ただし partial の
text は第1条項だけで、行の公式テキストには3条項ある。
条項はすべて確立済みの部品で表せる（追加語彙なし）:

- 「このクリーチャーはシールドをブレイクできない」は
  登録先例 dmex17-106 夢幻なる零龍（「このクリーチャーは
  シールドを１つもブレイクしない」）と同形の
  static {affects: self, mod: {breaks: 0}}。
  集約で break_opts が [0] になり、combat は
  counts=[0] のためブレイク自体が起きない（第129弾の
  ヌル・ブレイカーと同じ経路）。
- 「自分は「S・トリガー」能力を使えない」は登録先例
  dm04-022 暴風の求道者フ・レイル（「誰も闇のカードの
  S・トリガーを使えない」= static {affects: {owner: any,
  zone: shield, filter: {civs: [darkness]}}, mod:
  {deny: [s_trigger]}}）の変種: 対象が自分だけなので
  owner: you、文明フィルタは無し。proto T266
  （dmrp01-s03 型）も owner: you の同形。
- 「このカードは、４枚より多くデッキに入れることが
  できる」はデッキ構築ルールで、登録先例 dmex13-057 の
  注記どおりエンジン側に委ねる（テキストのみに残す）。

確立形: abilities = [static {affects: self, mod:
{breaks: 0}}, static {affects: {zone: shield, owner:
you}, mod: {deny: [s_trigger]}}] の2件。提出形では
text に行の公式テキスト全文を入れる（補完あり。
ラウンド404で対応すること）。

proto T1112（dmex03-061 型）。判別役は既存 proto を
流用: T1107（能力なしパワー2000アタッカー＝対照）、
T006（S・トリガー呪文＝破壊対象パワー4000以下）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED
が復活するので scenario.build を直接包む
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

BREAKS0 = {"kind": "static", "affects": "self", "mod": {"breaks": 0}}
STRIGGER_DENY = {"kind": "static",
                 "affects": {"zone": "shield", "owner": "you"},
                 "mod": {"deny": ["s_trigger"]}}
FORM = [BREAKS0, STRIGGER_DENY]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1112")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"] and c["civs"] == ["zero"]
    assert c["cost"] == 1 and c["power"] == 820
    assert c["races"] == ["ジョーカーズ"]
    d = parse_card(copy.deepcopy(c), TABLES)
    assert BREAKS0 in d.abilities and STRIGGER_DENY in d.abilities
    for tid in ("T1107", "T006"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX369", "name": "x",
                    "types": ["creature"], "civs": ["zero"],
                    "cost": 1, "power": 820, "mana": 1,
                    "races": ["ジョーカーズ"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert BREAKS0 in d.abilities and STRIGGER_DENY in d.abilities


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _find(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p) if e.cdef(c).id == defn)


def test_chars_break_opts_and_shield_deny(rules):
    """特性レベル: T1112 の break_opts は [0] ちょうど
    （対照の能力なしは [] で既定1）。自分のシールドは
    T1112 がいる間だけ deny [s_trigger] を持ち、
    相手のシールドには付かない。"""
    e = _build(rules, {"bz": ["T1112"]}, {})
    ch = e.chars(_find(e, "bz", 0, "T1112"))
    assert ch["break_opts"] == [0]
    e = _build(rules, {"bz": ["T1107"]}, {})
    ch = e.chars(_find(e, "bz", 0, "T1107"))
    assert ch["break_opts"] == []          # 対照: 既定の1ブレイク
    e = _build(rules, {"shield": ["T006"]}, {})
    assert e.chars(_find(e, "shield", 0, "T006"))["deny"] == []
    e = _build(rules, {"bz": ["T1112"], "shield": ["T006"]},
               {"shield": ["T006"]})
    assert "s_trigger" in e.chars(_find(e, "shield", 0, "T006"))["deny"]
    assert "s_trigger" not in e.chars(_find(e, "shield", 1, "T006"))["deny"]


def _drive(e, attacker, player, break_defn=None, use_strigger=False):
    """player の attacker でプレイヤーを攻撃する。
    break_defn があればそのシールドをブレイク対象に選び、
    declare_strigger の記録と use_strigger の使用可否を
    制御する。判断ログ [(kind, player, keys), ...] を返す。"""
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
            # S・トリガーの破壊対象などは攻撃側を選ぶ
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


def test_attack_breaks_no_shield(rules):
    """実挙動: T1112 がブロックされずにプレイヤーを
    攻撃しても、シールドは1枚もブレイクされない
    （攻撃自体は成立し、T1112 は場に残る）。"""
    e = _build(rules, {}, {"bz": ["T1112"]})
    before = len(e.zlist("shield", 0))
    _drive(e, "T1112", 1)
    assert len(e.zlist("shield", 0)) == before
    assert "T1112" in _defns(e, "bz", 1)


def test_control_attacker_breaks_one(rules):
    """対照: 能力なしのパワー2000（T1107）の攻撃は
    シールドを1枚ブレイクする。"""
    e = _build(rules, {}, {"bz": ["T1107"]})
    before = len(e.zlist("shield", 0))
    _drive(e, "T1107", 1)
    assert len(e.zlist("shield", 0)) == before - 1


def test_own_strigger_denied_while_source_present(rules):
    """実挙動: T1112 が自分の場にいる間、自分の
    シールド（T006）がブレイクされても S・トリガーの
    宣言判断自体が出ず、カードはそのまま手札に加わる
    （攻撃側は破壊されない）。"""
    e = _build(rules,
               {"bz": ["T1112"],
                "shield": ["T006", "T001", "T001", "T001", "T001"]},
               {"bz": ["T1107"]})
    log = _drive(e, "T1107", 1, break_defn="T006", use_strigger=True)
    assert not [x for x in log if x[0] == "declare_strigger"]
    assert "T006" in _defns(e, "hand", 0)
    assert "T1107" in _defns(e, "bz", 1)      # 破壊されていない
    assert len(e.zlist("shield", 0)) == 4


def test_strigger_usable_without_source(rules):
    """対照: T1112 がいなければ、ブレイクされた T006 は
    S・トリガーを宣言でき、使えば攻撃側（パワー2000）が
    破壊され、呪文は墓地に置かれる。"""
    e = _build(rules,
               {"shield": ["T006", "T001", "T001", "T001", "T001"]},
               {"bz": ["T1107"]})
    log = _drive(e, "T1107", 1, break_defn="T006", use_strigger=True)
    st = [x for x in log if x[0] == "declare_strigger"]
    assert st and st[0][1] == 0 and "strigger:T006" in st[0][2]
    assert "T1107" in _defns(e, "graveyard", 1)
    assert "T006" in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == 4


def test_opponent_strigger_unaffected(rules):
    """実挙動: deny は owner: you のため、相手の
    S・トリガー使用は妨げない。自分の T1107 が相手の
    T006 をブレイクすると、相手は宣言して使え、
    T1107 は破壊される。"""
    e = _build(rules,
               {"bz": ["T1112", "T1107"]},
               {"shield": ["T006", "T001", "T001", "T001", "T001"]})
    log = _drive(e, "T1107", 0, break_defn="T006", use_strigger=True)
    st = [x for x in log if x[0] == "declare_strigger"]
    assert st and st[0][1] == 1 and "strigger:T006" in st[0][2]
    assert "T1107" in _defns(e, "graveyard", 0)
    assert "T006" in _defns(e, "graveyard", 1)
    assert "T1112" in _defns(e, "bz", 0)
