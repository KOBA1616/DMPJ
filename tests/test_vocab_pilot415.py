"""語彙パイロット第415弾: battle_indestructible（ドリフト）。

センサス（rejects 1,917件を取り直し）: pure 1,769件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜414弾）は原則として再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021、
battle_opponent_reference の残り1件 dmr01-049、
untap_restriction の残り2件（dm26rp1-td004 /
dmx15-011、形が異なると判定済み）、cast_limit_
once_per_turn の multi 2件（dm26ex2-pr006 /
dm26ex4-cho031、他の gaps を併せ持つ）、
summoning_attack_rule の残り1件 dmex07-s01
（partial が素で条項未構築）、entered_turn_attack の
残り1件 dmbd11-d05（J・O・E 等が未構築）、madness の
残り1件 dmx26-028（CIP が look/reorder 系の未確立
機構）は先行弾の評価を覆す根拠が無く再提案しない。
destroyed_this_turn_condition と count_cards_drawn_
this_turn は次点のまま残す。distinct_civ_count
（3条項の複合）は後続候補のまま残す。first_time_tap
（pure 2、第410弾で記録）は新規語彙候補として
残置のまま。本弾で個別に評価して見送った候補:
trigger_when_battle_won（dm26ex4-052。バトル勝利時
誘発自体は第413弾で確立したが、マッハファイター／
パワード・ブレイカー／マナ数パワー／相手の初回攻撃の
強制先変更を含む複合）、turn_destroyed_count
（dm26rp2-std008。EXライフ＋攻撃時 look 複合＋
追加ターン条項）、ex_life_trigger（dm26rp3-008。
EXライフシールド離脱の照合が未確立）、same_power_
destroy（dm29-013。動的パワーフィルタが未確立で
第2条項も未構築の複合）、leave_trigger（dm37-045。
離脱誘発＋名前フィルタ回収の複合）、battle_lose_
stay（dmr02-004。バトル敗北時の滞留置換が未確立で
他条項も未構築の複合）、untap_trigger（dmr02-s01。
アンタップ時誘発が未確立で複合）、mana_leave_
trigger（dmr05-032。第366弾で却下済み）、battle_
win_destroy（dmr11-051。第413弾形そのものだが
partial が骨格のみで G・ゼロ／ブロッカー／攻撃不可
が未構築。次弾以降の候補として残す）、hand_add_
event（dmrp04s-s04。第366弾で却下済み）、
win_replacement（promoy14-056。勝利置換＋実世界
発話で範囲外寄り）、indestructible_while_blocking
（dmrp22-029。partial のコスト軽減 static に壊れた
フィルタが同居し本 gap 単独では定まらない）、
shield_plus_used_trigger（dmx10-023。op が
イベントを出さず検出不可）、draw_until_count
（dm24ex3-rp1s03。gap 名と実体がずれ複合）、
no_untap_until_next_own_turn_start（dm26rp1-s002。
Zラッシュ／ハイパー条項の複合）、destroy_after_
battle（dm07-003。ターン範囲の勝敗後処理付与が
未確立）、cross_event_trigger（dm16-033。クロス
誘発イベントが未確立）、attack_end_trigger
（dmrp21-002。攻撃の終わりの自己退場＋重ね置きが
未確立）。

範囲内・最小の **battle_indestructible（pure 1件、
multi にも現れない）** を選定した。対象行は partial
の無い素行（reason フィールドも無し。第393弾の
dmrp06-062 と同型）で、gap はラウンド59で細分済みの
既知ギャップ1件だけ。カード全体の2条項とも同一
文面の登録先例で直接表せる:

- 第1条項「自分の火の進化クリーチャーの召喚コストを
  最大２少なくする。ただしコストは０以下にならない」
  = static {affects: {owner: you, zone: hand,
  filter: {types: [evolution], civs: [fire]}},
  mod: {cost: -2, cost_min: 1}}。登録済み
  dm17-022 聖騎士ヴォイジャー（filter {types:
  [evolution]}、「最大２少なくなる／コストは１より
  少なくならない」で cost_min: 1）の形に文明フィルタ
  を足したもの。「コストは０以下にはならない」の
  下限1読みは登録済み dm24ex1-087 / dm24bd2-016
  （同文面で cost_min: 1）とも一致する。
- 第2条項「バトル中、このクリーチャーは破壊されない」
  = static {affects: self, mod:
  {battle_indestructible: true}}。第59弾の確立 mod
  の素形で、登録済み dm25rp3-055 / dmr21-077 が
  同一文面をこの形で登録済み（第366弾は条件つき版）。

対象は dmd27-012 燃えるメラッチ（火のクリーチャー /
コスト4 / パワー4000 / 種族 ファイアー・バード炎 /
革命軍）。行に partial が無いため骨格は公式データ行
（by_product/d27.jsonl）から決定的に構築し、text は
公式全文のため**補完なし**に相当する。alias は
dmr17-082 / promoy14-010 / promoy14-019 の3件
（いずれも同名）で rejects に独自行は無く、identity
実測で canon_id は対象自身、aliases_for = 3件。
第415弾時点で real.yaml / real_akashic.yaml /
real_vocab.yaml / real_zone.yaml / proto.yaml /
converted.yaml のいずれにも対象 id・alias とも
登録なし。単面カードで未検証の面は無い。登録
ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い＝
ツール側ブロッカーなし。対象行に reason フィールド
が無いため、ラウンド450では reopen の出力は0件の
はず（ラウンド423・428の実測）。

完全なドリフト（新規語彙・エンジン・defs・スキーマ
変更なし）。proto T1183（dmd27-012 型）。判別役は
既存 proto を流用: T328（火の進化・コスト3役）/
T077（水の進化・コスト3役）/ T1090（火の非進化・
コスト2役＋進化元役＋火マナ役）/ T1139（パワー
6000役）/ T1140（パワー4000ブロッカー役＝対照）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の
作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

REDUCE = {"kind": "static",
          "affects": {"owner": "you", "zone": "hand",
                      "filter": {"types": ["evolution"],
                                 "civs": ["fire"]}},
          "mod": {"cost": -2, "cost_min": 1}}
INDESTR = {"kind": "static", "affects": "self",
           "mod": {"battle_indestructible": True}}
FORM = [REDUCE, INDESTR]
FULL_TEXT = ("自分の火の進化クリーチャーの召喚コストを最大２少なくする。"
             "ただしコストは０以下にならない。"
             "バトル中、このクリーチャーは破壊されない。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1183")
    assert c["abilities"] == FORM
    assert c["name"] == "燃えるメラッチ"
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 4 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ファイアー・バード炎", "革命軍"]
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    for a in FORM:
        assert a in d.abilities
    for tid in ("T328", "T077", "T1090", "T1139", "T1140"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX415", "name": "燃えるメラッチ",
                    "types": ["creature"], "civs": ["fire"],
                    "cost": 4, "power": 4000, "mana": 1,
                    "races": ["ファイアー・バード炎", "革命軍"],
                    "text": FULL_TEXT,
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    for a in FORM:
        assert a in d.abilities
    assert len(d.abilities) == 2


def _bad(ability):
    with pytest.raises(DefError):
        parse_card({"id": "TX415B", "name": "x", "types": ["creature"],
                    "civs": ["fire"], "cost": 4, "power": 4000,
                    "abilities": [ability]}, TABLES)


def test_bad_unknown_filter_key():
    a = copy.deepcopy(REDUCE)
    a["affects"]["filter"]["bogus_key"] = 1
    _bad(a)


def test_bad_unknown_mod_key():
    a = copy.deepcopy(REDUCE)
    a["mod"]["bogus_mod"] = 1
    _bad(a)


def test_bad_cost_min_not_int():
    a = copy.deepcopy(REDUCE)
    a["mod"]["cost_min"] = "1"
    _bad(a)


def test_bad_unknown_civ_value():
    a = copy.deepcopy(REDUCE)
    a["affects"]["filter"]["civs"] = ["bogus_civ"]
    _bad(a)


def test_bad_indestructible_value():
    a = copy.deepcopy(INDESTR)
    a["mod"]["battle_indestructible"] = "yes"
    _bad(a)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _hand_cid(e, p, defn):
    return next(c for c in e.zlist("hand", p)
                if e.s.cards[c].defn == defn)


def _bz_cid(e, p, defn):
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn)


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def test_pay_cost_fire_evolution_reduced(rules):
    """第1条項の特性判別: 発生源がいれば、自分の
    火の進化（T328、コスト3）の支払いコストは
    3-2=1 になる。"""
    e = _build(rules, {"bz": ["T1183"], "hand": ["T328"]}, {})
    assert e.chars_ro(_hand_cid(e, 0, "T328"))["pay_cost"] == 1


def test_pay_cost_floor_with_two_sources(rules):
    """下限の判別: 発生源が2体いても支払いコストは
    1で止まる（cost_min: 1。「0以下にならない」。
    cost_min が 0 なら 3-4 で 0 になる）。"""
    e = _build(rules, {"bz": ["T1183", "T1183"], "hand": ["T328"]}, {})
    assert e.chars_ro(_hand_cid(e, 0, "T328"))["pay_cost"] == 1


def test_pay_cost_water_evolution_not_reduced(rules):
    """文明フィルタの判別: 水の進化（T077、コスト3）は
    軽減されず 3 のまま。"""
    e = _build(rules, {"bz": ["T1183"], "hand": ["T077"]}, {})
    assert e.chars_ro(_hand_cid(e, 0, "T077"))["pay_cost"] == 3


def test_pay_cost_fire_non_evolution_not_reduced(rules):
    """種別フィルタの判別: 火でも進化でない
    クリーチャー（T1090、コスト2）は軽減されず 2。"""
    e = _build(rules, {"bz": ["T1183"], "hand": ["T1090"]}, {})
    assert e.chars_ro(_hand_cid(e, 0, "T1090"))["pay_cost"] == 2


def test_pay_cost_no_source_control(rules):
    """対照: 発生源が無ければ火の進化（T328）も 3。"""
    e = _build(rules, {"hand": ["T328"]}, {})
    assert e.chars_ro(_hand_cid(e, 0, "T328"))["pay_cost"] == 3


def test_pay_cost_opponent_hand_not_reduced(rules):
    """owner: you の判別: 相手の手札の火の進化
    （T328）は、自分の発生源では軽減されない。"""
    e = _build(rules, {"bz": ["T1183"]}, {"hand": ["T328"]})
    assert e.chars_ro(_hand_cid(e, 1, "T328"))["pay_cost"] == 3


def _play_evolution(e, player=0, limit=600):
    """player が T328 を進化元 T1090 の上に召喚する
    まで進める（第409弾の _play と同型）。"""
    for _ in range(limit):
        if _in_zone(e, player, "bz", "T328"):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == player \
                and "play:T328" in keys:
            e.answer([keys.index("play:T328")])
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if any("T1090" in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if "T1090" in k)])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("play never happened")


def test_summon_fire_evolution_pays_one(rules):
    """第1条項の実挙動: 発生源と進化元（T1090）が
    いれば、火の進化 T328（コスト3）はマナ1枚の
    タップだけで召喚できる（残り2枚はアンタップ）。"""
    e = _build(rules,
               {"bz": ["T1183", "T1090"], "hand": ["T328"],
                "mana": ["T1090", "T1090", "T1090"]},
               {})
    _play_evolution(e)
    assert _in_zone(e, 0, "bz", "T328")
    tapped = sum(1 for c in e.zlist("mana", 0) if e.s.cards[c].tapped)
    assert tapped == 1


def _drive_battle(e, atk_player, atk_key, settle=1, limit=900):
    """atk_player の攻撃決定で atk_key を一度だけ
    選び、バトルを解決して settle ターン先まで進める。"""
    st = {"attacked": False, "attack_turn": None}
    for _ in range(limit):
        if st["attacked"] and e.s.turn > st["attack_turn"] + settle:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack" and d.get("player") == atk_player \
                and not st["attacked"] and atk_key in keys:
            st["attacked"] = True
            st["attack_turn"] = e.s.turn
            e.answer([keys.index(atk_key)])
            continue
        if kind == "declare_strigger":
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return st


def test_attack_loses_battle_but_not_destroyed(rules):
    """第2条項の判別（攻撃側）: T1183（パワー4000）が
    タップしている T1139（パワー6000）を攻撃して
    バトルに負けても、破壊されずバトルゾーンに残る
    （勝者の T1139 も残る）。"""
    e = _build(rules, {"bz": ["T1183"]}, {"bz": ["T1139"]})
    e.s.cards[_bz_cid(e, 1, "T1139")].tapped = True
    st = _drive_battle(e, 0, "attack:T1183:T1139")
    assert st["attacked"]
    assert _in_zone(e, 0, "bz", "T1183")
    assert not _in_zone(e, 0, "graveyard", "T1183")
    assert _in_zone(e, 1, "bz", "T1139")


def test_attack_control_without_indestructible_destroyed(rules):
    """対照: battle_indestructible の無い T1140
    （パワー4000）が同じ攻撃をすると、バトルに
    負けて破壊され墓地に置かれる。"""
    e = _build(rules, {"bz": ["T1140"]}, {"bz": ["T1139"]})
    e.s.cards[_bz_cid(e, 1, "T1139")].tapped = True
    st = _drive_battle(e, 0, "attack:T1140:T1139")
    assert st["attacked"]
    assert not _in_zone(e, 0, "bz", "T1140")
    assert _in_zone(e, 0, "graveyard", "T1140")
    assert _in_zone(e, 1, "bz", "T1139")


def test_attacked_loses_battle_but_not_destroyed(rules):
    """第2条項の判別（防御側）: T1183 がプレイヤーを
    攻撃してタップした後、T1139（パワー6000）に
    攻撃され、バトルに負けても破壊されず
    バトルゾーンに残る。"""
    e = _build(rules, {"bz": ["T1183"]}, {"bz": ["T1139"]})
    st1 = _drive_battle(e, 0, "attack:T1183:player", settle=0)
    assert st1["attacked"]
    assert e.s.cards[_bz_cid(e, 0, "T1183")].tapped is True
    st2 = _drive_battle(e, 1, "attack:T1139:T1183")
    assert st2["attacked"]
    assert _in_zone(e, 0, "bz", "T1183")
    assert not _in_zone(e, 0, "graveyard", "T1183")
    assert _in_zone(e, 1, "bz", "T1139")
