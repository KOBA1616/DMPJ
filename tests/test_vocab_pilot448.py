"""語彙パイロット第448弾: s_trigger_suppression（ドリフト＝
第435弾の復活）。

センサス（rejects 1,883件を取り直し）: pure 1,735件
（973家族）/ multi 130件 / 空 gaps 18件。pure の大半は
範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜447弾）と残置群（graveyard_replacement 残り
dm25ex2-cho021、battle_opponent_reference 残り
dmr01-049、untap_restriction 残り2件、does_not_untap
残り dm25ex2-031、revolution_2 残り dm26sd1-o004、
cast_limit_once_per_turn の multi 2件、
summoning_attack_rule 残り dmex07-s01、
entered_turn_attack 残り dmbd11-d05、madness 残り
dmx26-028、after_battle_trigger 残り dmrp09-074、
次点の destroyed_this_turn_condition /
count_cards_drawn_this_turn /
player_not_attacked_while_tapped /
mana_tap_placement、後続候補の distinct_civ_count、
新規語彙候補 first_time_tap / turn_history_entry /
played_free_condition、専用ステージ送りの
power_threshold_keyword_gain）は覆す根拠が無く
再提案しない。

本弾の選定は **s_trigger_suppression（pure 2件）のうち
dm28-025 ヤミノリミットのみ**。第435弾で「境界で公式と
食い違うため不成立」となり専用ステージ送りになったが、
113.6a 専用ステージ（HEAD 0d93622）が待機状態シールド
の数え分けを実装し、復活条件を満たした（同ステージ記録
参照）。形は第435弾の記録どおり、proto は同ステージが
追加した T1239（dm28-025 型、形そのもの）を流用する
（新規追加なし）。dm27-051 は発生源紐づけ
（broken_shields_no_s_trigger 側）の別機構のため
引き続き残置し、ファミリーは解消しない。

対象は dm28-025 ヤミノリミット（闇 / コスト4 /
パワー4000 / 種族 ダーク・モンスター / mana 1）。
partial は骨格完備（keywords・abilities ともに無し）
で、未解決は unsupported の s_trigger_suppression
1件だけ。**補完あり: text（公式全文。partial は条件部
「相手のシールドが４枚以上の時、」を落とした断片）
＋abilities**。alias は無し。

確立形（ドリフト）: static {affects: {zone: shield,
owner: opp}, if: {cmp: [{count: {zone: shield,
owner: opp}}, ">=", 4]}, mod: {deny: [s_trigger]}}
— 第374弾の deny [s_trigger] 形＋登録済み
dmr19-077 の count 条件の組み合わせ。新規語彙・
エンジン・スキーマ変更なし。

公式境界（第435弾の教訓＋113.6a）: 宣言時点の
シールド数はブレイクされた分を除いて数える。
5枚から1枚ブレイク → 4枚で条件成立（使えない）、
4枚から1枚ブレイク → 3枚で条件不成立（使える）、
5枚同時ブレイク → 宣言時点は3枚で使える（公式
Q&A 44581）、6枚から2枚同時ブレイク → 4枚で
使えない。特性レベル（ブレイク処理の外）では
ゾーンの実数がそのまま数えられる。

proto T1239（dm28-025 型。113.6a 専用ステージで
追加済み）。判別役は既存 proto を流用: T006
（S・トリガー呪文＝パワー4000以下を破壊）/
T1107（パワー2000・1ブレイク）/ T005
（W・ブレイカー・パワー3000・2ブレイク）/
T001（盾役・対照役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接包む（第319弾以降の作法）。
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

NAME = "ヤミノリミット"
TEXT = "相手のシールドが４枚以上の時、相手は自分自身の「S・トリガー」を使えない。"
STATIC = {"kind": "static",
          "affects": {"zone": "shield", "owner": "opp"},
          "if": {"cmp": [{"count": {"zone": "shield", "owner": "opp"}},
                         ">=", 4]},
          "mod": {"deny": ["s_trigger"]}}
FORM = {"name": NAME, "types": ["creature"],
        "civs": ["darkness"], "cost": 4, "power": 4000,
        "races": ["ダーク・モンスター"], "mana": 1,
        "text": TEXT, "abilities": [STATIC]}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1239")
    for k, v in FORM.items():
        assert c[k] == v, k
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.name == NAME
    assert STATIC in d.abilities
    for tid in ("T006", "T1107", "T005", "T001"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "X448", **copy.deepcopy(FORM)}, TABLES)
    assert d.name == NAME and d.power == 4000
    assert STATIC in d.abilities


def test_form_def_errors():
    base = {"id": "X448", **copy.deepcopy(FORM)}
    parse_card(copy.deepcopy(base), TABLES)
    # 未知の deny アクション
    bad = copy.deepcopy(base)
    bad["abilities"][0]["mod"]["deny"] = ["s_triggerr"]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # count の比較演算子誤り
    bad = copy.deepcopy(base)
    bad["abilities"][0]["if"]["cmp"][1] = "=>"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # 未知の mod キー
    bad = copy.deepcopy(base)
    bad["abilities"][0]["mod"]["denyy"] = ["s_trigger"]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # count セレクタの未知キー
    bad = copy.deepcopy(base)
    bad["abilities"][0]["if"]["cmp"][0]["count"]["foo"] = 1
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


# ---------- ドライバ ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _find(e, zone, p, defn, skip=0):
    hits = [c for c in e.zlist(zone, p) if e.cdef(c).id == defn]
    return hits[skip]


def _drive(e, attacker, player, break_defns, use_strigger=False):
    """player の attacker でプレイヤーを攻撃し、break_defns の
    順でシールドを選んでブレイクする。declare_strigger の
    判断ログ [(kind, player, keys), ...] を返す（第374弾の作法）。"""
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
        if kind == "choose_shields" and break_defns:
            shields = e.zlist("shield", 1 - player)
            want = list(break_defns)
            idx = []
            for i, c in enumerate(shields):
                if e.cdef(c).id in want:
                    idx.append(i)
                    want.remove(e.cdef(c).id)
            e.answer(idx)
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


# ---------- 実挙動: 特性レベル ----------

def test_chars_denied_at_4_not_at_3(rules):
    """特性レベル: 相手シールド4枚では deny が付き、
    3枚では付かない（ブレイク処理の外＝窓の外の評価）。"""
    e = _build(rules, {"bz": ["T1239"]},
               {"shield": ["T006", "T001", "T001", "T001"]})
    assert "s_trigger" in e.chars(_find(e, "shield", 1, "T006"))["deny"]
    e = _build(rules, {"bz": ["T1239"]},
               {"shield": ["T006", "T001", "T001"]})
    assert "s_trigger" not in e.chars(_find(e, "shield", 1, "T006"))["deny"]


def test_chars_own_shield_not_denied(rules):
    """特性レベル: 抑制は相手のシールドだけ。自分の
    シールドには deny が付かない（affects owner: opp）。"""
    e = _build(rules, {"bz": ["T1239"], "shield": ["T006"]},
               {"shield": ["T006", "T001", "T001", "T001"]})
    assert "s_trigger" not in e.chars(_find(e, "shield", 0, "T006"))["deny"]
    assert "s_trigger" in e.chars(_find(e, "shield", 1, "T006"))["deny"]


# ---------- 実挙動: ブレイク時の宣言 ----------

def test_break_from_4_usable(rules):
    """判別: 相手シールド4枚から1枚ブレイク → 宣言時点は
    3枚で条件不成立となり、S・トリガーを宣言できる。
    使えば攻撃側（パワー2000）が破壊される。解決後の
    特性評価も残り3枚で deny が付かない。"""
    e = _build(rules,
               {"bz": ["T1239", "T1107"]},
               {"shield": ["T006", "T006", "T001", "T001"]})
    log = _drive(e, "T1107", 0, ["T006"], use_strigger=True)
    st = [x for x in log if x[0] == "declare_strigger"]
    assert st and st[0][1] == 1 and "strigger:T006" in st[0][2]
    assert "T1107" in _defns(e, "graveyard", 0)
    assert "T006" in _defns(e, "graveyard", 1)
    assert len(e.zlist("shield", 1)) == 3
    rest = _find(e, "shield", 1, "T006")
    assert "s_trigger" not in e.chars(rest)["deny"]


def test_break_from_5_denied(rules):
    """対照: 相手シールド5枚から1枚ブレイク → 宣言時点は
    4枚で条件成立のまま、宣言判断自体が出ずカードは手札へ。
    攻撃側は破壊されない。"""
    e = _build(rules,
               {"bz": ["T1239", "T1107"]},
               {"shield": ["T006", "T001", "T001", "T001", "T001"]})
    log = _drive(e, "T1107", 0, ["T006"], use_strigger=True)
    assert not [x for x in log if x[0] == "declare_strigger"]
    assert "T006" in _defns(e, "hand", 1)
    assert "T1107" in _defns(e, "bz", 0)
    assert len(e.zlist("shield", 1)) == 4


def test_break_two_from_5_usable(rules):
    """判別（同時ブレイク）: W・ブレイカーで5枚から2枚同時
    ブレイク → 宣言時点は3枚で条件不成立、宣言できる。
    公式 Q&A 44581 の同時ブレイクの読みと同方向。使えば
    攻撃側（パワー3000）が破壊される。"""
    e = _build(rules,
               {"bz": ["T1239", "T005"]},
               {"shield": ["T006", "T001", "T001", "T001", "T001"]})
    log = _drive(e, "T005", 0, ["T006", "T001"], use_strigger=True)
    st = [x for x in log if x[0] == "declare_strigger"]
    assert st and st[0][1] == 1 and "strigger:T006" in st[0][2]
    assert "T005" in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 1)) == 3


def test_break_two_from_6_denied(rules):
    """対照（同時ブレイク）: 6枚から2枚同時ブレイク →
    宣言時点は4枚で条件成立のまま、宣言できない。
    カードは手札へ。"""
    e = _build(rules,
               {"bz": ["T1239", "T005"]},
               {"shield": ["T006", "T001", "T001", "T001", "T001", "T001"]})
    log = _drive(e, "T005", 0, ["T006", "T001"], use_strigger=True)
    assert not [x for x in log if x[0] == "declare_strigger"]
    assert "T006" in _defns(e, "hand", 1)
    assert len(e.zlist("shield", 1)) == 4
