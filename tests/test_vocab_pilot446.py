"""語彙パイロット第446弾: blocker_cost_restriction
（ドリフト）。

センサス（rejects 1,885件を取り直し）: pure
1,634件（894家族）/ multi 130件 / 空 gaps 18件。
pure の大半は範囲外（gr_summon 146 / aura 108
＝未承認 / hyperdimensional_zone 105 /
psychic_filter 45 / dragheart 44 /
hyperdimensional_summon 39 / out_of_game 23 /
duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜445弾）と残置群（graveyard_replacement
残り dm25ex2-cho021、battle_opponent_reference
残り dmr01-049、untap_restriction 残り2件、
does_not_untap 残り dm25ex2-031、revolution_2
残り dm26sd1-o004、cast_limit_once_per_turn の
multi 2件、summoning_attack_rule 残り
dmex07-s01、entered_turn_attack 残り
dmbd11-d05、madness 残り dmx26-028、
after_battle_trigger 残り dmrp09-074、
s_trigger_suppression＝専用ステージ送り、次点の
destroyed_this_turn_condition /
count_cards_drawn_this_turn /
player_not_attacked_while_tapped /
mana_tap_placement、後続候補の
distinct_civ_count、新規語彙候補 first_time_tap
/ turn_history_entry / played_free_condition）
は覆す根拠が無く再提案しない。本弾で個別に
評価して見送った候補: attack_target_power_filter
（pure 1、dmr15-030。gap 名は power だが公式は
コスト制限で第444弾の登録形と同形＝表現可能
だが次点に残す）、conditional_tapped_state
（pure 1。2静的効果の複合で最小でない）、
shield_event_condition（pure 2。ターン履歴条件
で未確立）、force_attack_target（pure 2。複合／
異形）、first_turn_attack_trigger（pure 2。
複合）、after_attack_destroy（pure 2。複合）、
no_untap_while_source_tapped（pure 1。stub 行）。

範囲内・最小の **blocker_cost_restriction
（pure 1件、multi にも現れない）** を選定した。
対象は dmr05-105 ヌケッピ・サンナン。行の注記
「ブロッカーのコスト制限を表す語彙が無い」は
陳腐化: 条項「このクリーチャーは、コスト６
以下のクリーチャーにブロックされない」は
static {affects: self, mod: {deny: [{action:
be_blocked, other: {cost_le: 6}}]}} で表せる。
- deny の辞書形 {action: be_blocked, other:
  {power_le: 4000}} は登録済み dm01-009
  （シェル・タワー）の登録形そのもの。
- other フィルタの cost_le は第444弾の登録形
  （be_attacked × cost_le 6）で実測済みで、
  other の評価は action に依らない共通経路。
新規語彙・エンジン・defs・スキーマ変更なし
＝ドリフト（be_blocked × cost_le は既存部品の
組み合わせの初使用）。もう1条項のハンティング
はキーワード hunting の確立形（parse で
battle_power の keyword マーカーつき static に
正規化される）。

partial は骨格完備（text 公式全文、keywords
[hunting]）で abilities 未構築、unsupported は
本条項1件のみ。**補完あり: abilities**
（deny static 1件）。alias は無し（identity
実測で canon は対象自身）。

公式境界: 「ブロックされない」はブロック宣言
の合法性だけを制限し、攻撃される側の制限とは
独立。境界は「6以下」＝コスト6のブロッカーは
ブロックできず、コスト7はブロックできる。

proto T1237（dmr05-105 型）。判別役は既存の
T309（コスト6ブロッカー・パワー5000＝境界）/
T120（コスト7ブロッカー・パワー9000）/
T004（コスト3ブロッカー・パワー3000）/
T797（コスト2・パワー2500＝ハンティング判別）/
T040（コスト7・パワー6000＝被攻撃判別）。

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
               "mod": {"deny": [{"action": "be_blocked",
                                 "other": {"cost_le": 6}}]}}

NAME = "ヌケッピ・サンナン"
TEXT = ("ハンティング(バトル中、このクリーチャーのパワーは、"
        "バトルゾーンにある自分のハンター１体につき+1000される)\n"
        "このクリーチャーは、コスト６以下のクリーチャーにブロックされない。")
FORM = {"name": NAME, "types": ["creature"],
        "civs": ["nature"], "cost": 4, "power": 2000,
        "races": ["ファイアー・バード", "ハンター"], "mana": 1,
        "keywords": ["hunting"],
        "text": TEXT, "abilities": [DENY_STATIC]}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1237")
    for k, v in FORM.items():
        assert c[k] == v, k
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.name == NAME
    # ハンティングは keyword マーカーつき static に
    # 正規化され、残りが FORM の deny static と一致する
    kw = [a for a in d.abilities if "keyword" in a]
    assert len(kw) == 1 and kw[0]["keyword"] == "hunting"
    plain = [a for a in d.abilities if "keyword" not in a]
    assert plain == FORM["abilities"]


def test_form_def_errors():
    base = {"id": "X446", **copy.deepcopy(FORM)}
    parse_card(copy.deepcopy(base), TABLES)
    # deny 項目の未知アクション
    bad = copy.deepcopy(base)
    bad["abilities"][0]["mod"]["deny"][0]["action"] = "be_blockedd"
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


def _drive(e, attacks=(), blocker=None, stop=None, limit=1500):
    """attacks（攻撃キーの列）を順に一度ずつ実行する。
    block 決定の選択肢は st["block_logs"] に記録し、
    blocker（proto id）が選択肢にあればそれを選び、
    無ければ no_block を選ぶ。stop が真になったら止める。"""
    st = {"done": [], "block_logs": []}
    queue = list(attacks)
    for _ in range(limit):
        if stop and stop():
            return st
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if d["kind"] == "block":
            st["block_logs"].append(list(keys))
            if blocker:
                hit = [i for i, k in enumerate(keys)
                       if k and k.startswith(f"bz:{blocker}")]
                if hit:
                    e.answer([hit[0]])
                    continue
            e.answer([keys.index("no_block")])
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


# ---------- 実挙動 ----------

def test_cost6_blocker_cannot_block(rules):
    """境界: コスト6のブロッカー T309（パワー5000）は
    T1237 をブロックできない。block 決定の選択肢に
    bz:T309 が現れず、攻撃は通ってシールドが1枚
    割れる。T1237 は場に残る。"""
    e = _build(rules, {"bz": ["T1237"]}, {"bz": ["T309"]})
    src = _cid(e, 0, "T1237")
    blk = _cid(e, 1, "T309")
    st = _drive(e, attacks=["attack:T1237:player"],
                stop=lambda: len(e.zlist("shield", 1)) == 4)
    assert st["done"] == ["attack:T1237:player"]
    assert all(not any(k and k.startswith("bz:T309") for k in ks)
               for ks in st["block_logs"])
    assert _zone(e, src) == "bz"
    assert _zone(e, blk) == "bz"
    assert not e.s.cards[blk].tapped


def test_cost3_blocker_cannot_block(rules):
    """コスト3のブロッカー T004 もブロックできない
    （コスト帯の下側の判別）。"""
    e = _build(rules, {"bz": ["T1237"]}, {"bz": ["T004"]})
    src = _cid(e, 0, "T1237")
    st = _drive(e, attacks=["attack:T1237:player"],
                stop=lambda: len(e.zlist("shield", 1)) == 4)
    assert st["done"] == ["attack:T1237:player"]
    assert all(not any(k and k.startswith("bz:T004") for k in ks)
               for ks in st["block_logs"])
    assert _zone(e, src) == "bz"


def test_cost7_blocker_can_block(rules):
    """コスト7のブロッカー T120（パワー9000）は
    ブロックできる: 選択肢に bz:T120 が現れ、
    ブロックするとバトル（T1237 はハンティングで
    3000）で T1237 は破壊され、シールドは減らない。"""
    e = _build(rules, {"bz": ["T1237"]}, {"bz": ["T120"]})
    src = _cid(e, 0, "T1237")
    blk = _cid(e, 1, "T120")
    st = _drive(e, attacks=["attack:T1237:player"], blocker="T120",
                stop=lambda: _zone(e, src) == "graveyard")
    assert st["done"] == ["attack:T1237:player"]
    assert any(any(k and k.startswith("bz:T120") for k in ks)
               for ks in st["block_logs"])
    assert _zone(e, blk) == "bz"
    assert len(e.zlist("shield", 1)) == 5


def test_hunting_power_in_battle(rules):
    """ハンティングの判別: タップした T797
    （パワー2500）を攻撃すると、バトル中の
    パワーは 2000＋1000（自分のハンター＝自身）
    ＝3000 になり T797 を破壊して場に残る
    （ハンティングが無ければ 2000＜2500 で負ける）。"""
    e = _build(rules, {"bz": ["T1237"]}, {"bz": ["T797"]})
    src = _cid(e, 0, "T1237")
    tgt = _cid(e, 1, "T797")
    e.s.cards[tgt].tapped = True
    st = _drive(e, attacks=["attack:T1237:T797"],
                stop=lambda: _zone(e, tgt) == "graveyard")
    assert st["done"] == ["attack:T1237:T797"]
    assert _zone(e, src) == "bz"


def test_can_be_attacked_normally(rules):
    """deny は be_blocked だけなので、T1237 は
    通常どおり攻撃される: プレイヤーを攻撃して
    タップした T1237 を、コスト7の T040 が攻撃
    でき、バトル（6000 vs バトル中3000）で
    T1237 は破壊される。"""
    e = _build(rules, {"bz": ["T1237"]}, {"bz": ["T040"]})
    src = _cid(e, 0, "T1237")
    atk = _cid(e, 1, "T040")
    st = _drive(e, attacks=["attack:T1237:player",
                            "attack:T040:T1237"],
                stop=lambda: _zone(e, src) == "graveyard")
    assert st["done"] == ["attack:T1237:player",
                          "attack:T040:T1237"]
    assert _zone(e, atk) == "bz"
