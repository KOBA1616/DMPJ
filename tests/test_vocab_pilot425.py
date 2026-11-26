"""語彙パイロット第425弾: battle_power_filter。

センサス（rejects 1,907件を取り直し）: pure 1,759 /
multi 130 / 空 gaps 18。pure の大半は範囲外（gr_summon
147 / aura 108＝未承認 / hyperdimensional_zone 105 /
dragheart 45 / psychic_filter 45 / hyperdimensional_summon
41 / out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。残りは pure 1〜4件の小家族が多数。
評価済み却下（第316〜320・355〜424弾）は再提案しない。
残置群（dm25ex2-cho021、dmr01-049、untap_restriction
残り2件、dm25ex2-031、cast_limit multi 2件、dmex07-s01、
dmbd11-d05、dmx26-028、次点の destroyed_this_turn_condition /
count_cards_drawn_this_turn、distinct_civ_count、
first_time_tap）は覆す根拠が無く再提案しない。本弾で
個別に評価して見送った候補:
- additional_cost 系（dm03-029 / dmex08-090＝同一カード
  魔流毒の別名 gap、dm06-s06）: 詠唱・攻撃の追加コスト
  （自分の闇クリーチャーの破壊・生け贄）の確立形が無い。
  sac_reduce は召喚コスト軽減の別機構で代用できない。
- arithmetic_count（dmex17-087）: 5−シールド数の
  差し引き式に加え、第1条項（シールドを手札に加える・
  そのS・トリガーは使えない）も複合で最小でない。
- being_attacked_power（dm39-036）: 「攻撃されている間」
  は攻撃対象の状態で、battle_power（only 無し）は自分が
  攻撃するバトルにも効いて一致しない。power_when の
  blocking はブロック成立後の状態で、攻撃対象だが
  ブロックされていない状態を覆わない。確立形が無い。
- blocker_dies_after_battle_even_if_wins（dm01-028）:
  ブロックした相手全体へのスレイヤー的付与は通常の
  スレイヤー付与では攻撃時まで広がり代用できない。
- battle_win_grant（dmc67-016）: 「バトルに勝たせる」
  付与の確立形が無い。
- attack_end_trigger（dmrp21-002）: 攻撃の終わりの
  自己退場＋タマシードへの重ね置きの複合。
- all_mana_multicolor_cond（dmrp10-030）: partial が
  x/y の仮面 stub で faces 自体が未構築。

選定: battle_power_filter（pure 1件のみ、multi にも
現れない）— dmr08-009 巨体の守護者ランチュン。
行の注記「バトル相手の条件つきパワーを表す語彙が無い」
は第122弾より前の陳腐化した評価。第122弾で確立した
battle_power {amount, opponent_filter} のフィルタ
差し替え版で、第377弾（civs: [light] 版）、第378弾
（power_ge: 12000 版）と同形の完全なドリフト。
filter の cost_le は FILTER_KEYS / FILTER_EXPR_KEYS
の既存キー。defs の battle_power 検証は opponent_filter
を filter 検証に通し、schema.py の battle_power 定義
にも opponent_filter {filter} があり filter 定義に
cost_le がある（第408弾の教訓で両側の同期を確認済み。
スキーマ再生成は不要）。エンジン側は combat.py の
_battle_bonus が filter_match（相手の特性値）で照合し、
only 無しでは攻撃・防御の両バトルに効く（第122・
377・378・391弾の確立解釈）。
新規語彙なし・エンジン変更なし。

公式テキスト:
「ブロッカー(相手クリーチャーが攻撃する時、この
クリーチャーをタップして、その攻撃を阻止してもよい。
その後、その相手クリーチャーとバトルする)／
このクリーチャーは、相手プレイヤーを攻撃できない。／
コスト６以下のクリーチャーとバトル中、この
クリーチャーのパワーは+2000される。」
- 第1・第2条項は partial に keywords [blocker,
  cannot_attack_player] として構築済み。
- 第3条項は static {affects: self, mod: {battle_power:
  {amount: 2000, opponent_filter: {cost_le: 6}}}}。
partial は骨格＋keywords まで構築済みで abilities は
無く、text は公式全文（公式データ行 by_product/
r08.jsonl と全文一致。補完なし）。alias は無し
（identity 実測で canon_id は対象自身、aliases_for
= []）。単面カードで未検証の面は無い。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.split
（対象行）は (["blocker", "cannot_attack_player"],
第3条項テキスト, []) を返し、定型所有はキーワードのみで
part[2] の能力所有は空。ラウンド460は通常どおり
submit できる見込み。

プロト: T1201 = dmr08-009 型。T1202 = コスト5・
パワー5000バニラ（上限以下: 素4000では負け、+2000 で
勝つ判別役）、T1203 = コスト7・パワー5000バニラ
（上限超え: 加算が付かず負ける対照役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
バトルゾーンは共有ゾーンなので所有は bz_tops(p) /
zlist(zone, p) で見る。parse_card は blocker /
cannot_attack_player キーワードを常在型に展開するので、
parse 後の abilities は包含で確認する（第372弾の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

STATIC = {"kind": "static", "affects": "self",
          "mod": {"battle_power": {"amount": 2000,
                                   "opponent_filter": {"cost_le": 6}}}}
FORM = [STATIC]
FULL_TEXT = ("ブロッカー(相手クリーチャーが攻撃する時、このクリーチャーをタップして、"
             "その攻撃を阻止してもよい。その後、その相手クリーチャーとバトルする)\n"
             "このクリーチャーは、相手プレイヤーを攻撃できない。\n"
             "コスト６以下のクリーチャーとバトル中、このクリーチャーのパワーは+2000される。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form():
    proto = proto_card("T1201")
    assert proto["abilities"] == FORM
    assert proto["keywords"] == ["blocker", "cannot_attack_player"]
    assert proto["text"] == FULL_TEXT
    assert proto["mana"] == 1
    d = parse_card(proto, TABLES)
    assert STATIC in d.abilities
    assert d.types == ["creature"]
    assert d.civs == ["light"]
    assert d.cost == 3 and d.power == 4000
    assert d.races == ["ガーディアン"]
    assert d.keywords == ["blocker", "cannot_attack_player"]


def test_bad_opponent_filter_rejected():
    bad = dict(proto_card("T1201"))
    bad["abilities"] = [{"kind": "static", "affects": "self",
                         "mod": {"battle_power":
                                 {"amount": 2000,
                                  "opponent_filter": {"bogus": 1}}}}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def test_bad_battle_power_key_rejected():
    bad = dict(proto_card("T1201"))
    bad["abilities"] = [{"kind": "static", "affects": "self",
                         "mod": {"battle_power":
                                 {"amount": 2000, "bogus": 1}}}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _blocked_battle(e, attacker_p, attacker, blocker):
    """attacker_p の attacker がプレイヤーを攻撃し、相手が
    blocker でブロックする。バトルが終わって attacker_p の
    次の charge が来たら戻る。"""
    state = {}
    for _ in range(3000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == attacker_p \
                and state.get("blocked"):
            return state
        if d["kind"] == "attack" and d.get("player") == attacker_p \
                and not state.get("attacked"):
            tgt = [k for k in keys if k == f"attack:{attacker}:player"]
            if tgt:
                state["attacked"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "block":
            pick = [i for i, k in enumerate(keys)
                    if k.startswith(f"bz:{blocker}")]
            if pick:
                state["blocked"] = True
                e.answer([pick[0]])
            else:
                e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("battle never finished")


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _tops(e, p):
    return [e.s.cards[c].defn for c in e.bz_tops(p)]


def test_block_beats_cost5_with_bonus(rules):
    # コスト5・パワー5000のアタッカーをブロック:
    # 素4000では負けるが +2000=6000 で勝つ
    e = _build(rules, {"bz": ["T1201"]}, {"bz": ["T1202"]})
    state = _blocked_battle(e, 1, "T1202", "T1201")
    assert state.get("attacked") and state.get("blocked"), state
    assert "T1202" in _defns(e, "graveyard", 1)
    assert "T1201" in _tops(e, 0)


def test_block_loses_to_cost7_without_bonus(rules):
    # コスト7・パワー5000のアタッカーをブロック:
    # コスト上限を超えるので加算は付かず 4000<5000 で負ける
    e = _build(rules, {"bz": ["T1201"]}, {"bz": ["T1203"]})
    state = _blocked_battle(e, 1, "T1203", "T1201")
    assert state.get("attacked") and state.get("blocked"), state
    assert "T1201" in _defns(e, "graveyard", 0)
    assert "T1203" in _tops(e, 1)


def _attack_creature_battle(e, target):
    """p1 の target がプレイヤーを攻撃してタップした後、
    p0 の T1201 がそのタップした target を攻撃する。
    バトルが終わって p1 の次の charge が来たら戻る。"""
    state = {}
    for _ in range(3000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 1 \
                and state.get("battled"):
            return state
        if d["kind"] == "attack" and d.get("player") == 1 \
                and not state.get("p1_attacked"):
            tgt = [k for k in keys if k == f"attack:{target}:player"]
            if tgt:
                state["p1_attacked"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "attack" and d.get("player") == 0 \
                and state.get("p1_attacked") and not state.get("battled"):
            tgt = [k for k in keys if k == f"attack:T1201:{target}"]
            if tgt:
                state["battled"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("battle never finished")


def test_attack_beats_cost5_with_bonus(rules):
    # 攻撃側でも「バトル中」は効く（battle_power は only
    # 無しで両バトルに効く）: タップしたコスト5・
    # パワー5000 を攻撃し、+2000=6000 で勝つ
    e = _build(rules, {"bz": ["T1201"]}, {"bz": ["T1202"]})
    state = _attack_creature_battle(e, "T1202")
    assert state.get("p1_attacked") and state.get("battled"), state
    assert "T1202" in _defns(e, "graveyard", 1)
    assert "T1201" in _tops(e, 0)


def test_attack_loses_to_cost7_without_bonus(rules):
    # タップしたコスト7・パワー5000 を攻撃: 加算は
    # 付かず 4000<5000 で負ける
    e = _build(rules, {"bz": ["T1201"]}, {"bz": ["T1203"]})
    state = _attack_creature_battle(e, "T1203")
    assert state.get("p1_attacked") and state.get("battled"), state
    assert "T1201" in _defns(e, "graveyard", 0)
    assert "T1203" in _tops(e, 1)


def test_no_bonus_outside_battle(rules):
    # バトル中でなければパワーは素の 4000 のまま
    # （battle_power はバトル中専用の修整）
    e = _build(rules, {"bz": ["T1201"]}, {"bz": ["T1202"]})
    cid = next(c for c in e.zlist("bz", 0)
               if e.s.cards[c].defn == "T1201")
    assert e.chars(cid)["power"] == 4000
