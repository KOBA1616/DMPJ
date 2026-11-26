"""語彙パイロット第416弾: fixed_breaks_plus_one（ドリフト）。

センサス（rejects 1,916件を取り直し）: pure 1,768件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜415弾）は原則として再提案しない。
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
残置のまま。

範囲内・最小の **fixed_breaks_plus_one（pure 1件、
multi にも現れない）** を選定した。第415弾で次点として
新規に記録された候補であり、本弾で modify 内の
breaks_add の実挙動と Jチェンジ6の閾値形を検証して
選定した。対象行は round66 由来の素行（partial も
reason フィールドも無し。note は「シールドをさらに
１つブレイクする。modify で固定+1のブレイク数増加を
表す語彙がない」）で、第361弾で「テキスト・partial
が無く評価不能」とされたのは公式データ行
（by_product/rp07.jsonl）から骨格と全文が引けるため
解消する（第393・415弾と同型の素行処理）。カード
全体の2条項とも登録先例で直接表せる完全なドリフト:

- 第1条項「Jチェンジ６」= trigger {when:
  {event: attack, subject: self}, effect: [may
  [swap {out: {ref: self}, out_to: mana, in:
  {zone: mana, owner: you, filter: {types:
  [creature], cost_le: 6, race_has: ジョーカーズ},
  count: 1}}]]}。第24弾の確立形で、同セットの
  登録済み dmrp07-027 おテントさん（同一文面の
  Jチェンジ６）の登録形と完全一致。
- 第2条項「このクリーチャーがバトルゾーンに出た時、
  そのターン、自分の他のクリーチャー１体のパワーは
  +4000され、シールドをさらに１つブレイクする」
  = trigger {when: {event: move, to: bz, subject:
  self}, effect: [choose {select: {zone: bz,
  owner: you, filter: {types: [creature]}, other:
  true, count: 1}, as: pick}, modify {select:
  {ref: pick}, mod: {power: 4000, breaks_add: 1},
  duration: end_of_turn}]}。modify の mod に
  power と breaks_add を併記する形は登録済み
  dmr19-047 煽動の面 フリント（第159弾）の先例が
  あり、行の note の「固定+1の語彙がない」は
  breaks_add（第360弾で static 側に確立、集約は
  modify 由来も対象）の見落としだった。「自分の
  他の」は selector の other: true（第379弾）。
  choose→ref は第389・395・414弾の確立パターン。

対象は dmrp07-052 C.W.テラス（自然のクリーチャー /
コスト4 / パワー4000 / 種族 ジョーカーズ）。行に
partial が無いため骨格は公式データ行
（by_product/rp07.jsonl）から決定的に構築し、text は
公式全文（改行あり）のため**補完なし**に相当する。
alias は無し（identity 実測で canon_id は対象自身、
aliases_for = []）。第416弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも登録なし。
単面カードで未検証の面は無い。登録ブロッカーの
確認（第375弾の教訓）: rule_convert.split（対象行）
は None を返し定型所有は無い＝ツール側ブロッカー
なし。対象行に reason フィールドが無いため、
ラウンド451では reopen の出力は0件のはず
（ラウンド423・428・450の実測）。

完全なドリフト（新規語彙・エンジン・defs・スキーマ
変更なし。swap / choose / modify / breaks_add /
other / race_has / cost_le はすべて既存キーで、
生成スキーマ data/schema/card.schema.json にも
定義済みを本弾で確認）。proto T1184（dmrp07-052 型）。
判別役: T068（ジョーカーズ・コスト3役＝入れ替え先）/
T1185（ジョーカーズ・コスト7役＝閾値超過）/
T001（自然バニラ・パワー2000役＝CIP の対象・
非ジョーカーズのマナ役）/ T1139（パワー6000役＝
2体目の味方・選択判別）。

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

JCHANGE = {"kind": "trigger",
           "when": {"event": "attack", "subject": "self"},
           "effect": [{"op": "may", "body": [
               {"op": "swap", "out": {"ref": "self"}, "out_to": "mana",
                "in": {"zone": "mana", "owner": "you",
                       "filter": {"types": ["creature"], "cost_le": 6,
                                  "race_has": "ジョーカーズ"},
                       "count": 1}}]}]}
CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "effect": [
           {"op": "choose",
            "select": {"zone": "bz", "owner": "you",
                       "filter": {"types": ["creature"]},
                       "other": True, "count": 1},
            "as": "pick"},
           {"op": "modify", "select": {"ref": "pick"},
            "mod": {"power": 4000, "breaks_add": 1},
            "duration": "end_of_turn"}]}
FORM = [JCHANGE, CIP]
FULL_TEXT = ("Jチェンジ６（このクリーチャーが攻撃する時、このクリーチャーと"
             "自分のマナゾーンにあるコスト６以下のジョーカーズ１体を"
             "入れ替えてもよい）\n"
             "このクリーチャーがバトルゾーンに出た時、そのターン、自分の"
             "他のクリーチャー１体のパワーは+4000され、シールドをさらに"
             "１つブレイクする。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1184")
    assert c["abilities"] == FORM
    assert c["name"] == "C.W.テラス"
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 4 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ジョーカーズ"]
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    for a in FORM:
        assert a in d.abilities
    for tid in ("T068", "T1185", "T001", "T1139"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX416", "name": "C.W.テラス",
                    "types": ["creature"], "civs": ["nature"],
                    "cost": 4, "power": 4000, "mana": 1,
                    "races": ["ジョーカーズ"],
                    "text": FULL_TEXT,
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    for a in FORM:
        assert a in d.abilities
    assert len(d.abilities) == 2


def _bad(ability):
    with pytest.raises(DefError):
        parse_card({"id": "TX416B", "name": "x", "types": ["creature"],
                    "civs": ["nature"], "cost": 4, "power": 4000,
                    "abilities": [ability]}, TABLES)


def test_bad_swap_in_filter_key():
    a = copy.deepcopy(JCHANGE)
    a["effect"][0]["body"][0]["in"]["filter"]["bogus_key"] = 1
    _bad(a)


def test_bad_breaks_add_value():
    a = copy.deepcopy(CIP)
    a["effect"][1]["mod"]["breaks_add"] = "1"
    _bad(a)


def test_bad_choose_unknown_selector_key():
    a = copy.deepcopy(CIP)
    a["effect"][0]["select"]["bogus_key"] = 1
    _bad(a)


def test_bad_unknown_mod_key():
    a = copy.deepcopy(CIP)
    a["effect"][1]["mod"]["bogus_mod"] = 1
    _bad(a)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn, zone="bz"):
    return next(c for c in e.zlist(zone, p)
                if e.s.cards[c].defn == defn)


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _drive(e, player=0, play=None, pick=None, attack=None,
           swap_pick=None, swap_decline=False, turns=0,
           stop_after_pick=False, stop_at_attack=False, limit=900):
    """player のターンを進める汎用ドライバ（第409・415弾
    と同型）。play で召喚し、choose_cards で pick を
    含む選択肢を CIP の対象に選び、attack で攻撃する。
    swap_pick は choose_cards で Jチェンジ先として
    選ぶ（候補が1体だけなら自動選択され決定は出ない。
    yes_no は yes）。swap_decline の時は yes_no に
    no と答える。turns は対象ターンを何ターン先まで
    進めるか。stop_after_pick は対象を選んだ直後の
    決定で止め、stop_at_attack は召喚後の最初の
    攻撃決定で止める（いずれもターン内の特性を
    見るため）。"""
    st = {"played": False, "picked": False, "attacked": False,
          "target_turn": None}
    for _ in range(limit):
        if st["target_turn"] is not None \
                and e.s.turn > st["target_turn"] + turns:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        pl = d.get("player")
        if kind in ("charge", "main", "attack") and pl == player \
                and st["target_turn"] is None:
            st["target_turn"] = e.s.turn
        if stop_after_pick and st["picked"]:
            break
        if stop_at_attack and st["played"] and kind == "attack" \
                and pl == player:
            break
        if play and not st["played"] and kind == "main" \
                and pl == player and f"play:{play}" in keys:
            st["played"] = True
            e.answer([keys.index(f"play:{play}")])
            continue
        if swap_decline and kind == "yes_no" and "no" in keys:
            e.answer([keys.index("no")])
            continue
        if kind == "yes_no" and "yes" in keys:
            e.answer([keys.index("yes")])
            continue
        if swap_pick and kind == "choose_cards" \
                and any(swap_pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if swap_pick in k)])
            continue
        if pick and not st["picked"] and kind == "choose_cards" \
                and any(pick in k for k in keys):
            st["picked"] = True
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
            continue
        if attack and not st["attacked"] and kind == "attack" \
                and pl == player and attack in keys:
            st["attacked"] = True
            e.answer([keys.index(attack)])
            continue
        if kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "declare_strigger":
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return st


def test_cip_buffs_chosen_other_creature(rules):
    """第2条項の特性判別: 出た時、選んだ他の
    クリーチャー（T1139、パワー6000）だけが
    +4000 され 10000 になる。選ばなかった T001
    （2000）と発生源自身（4000）は変わらない
    （other: true の判別を含む）。"""
    e = _build(rules,
               {"bz": ["T001", "T1139"], "hand": ["T1184"],
                "mana": ["T001", "T001", "T001", "T001"]},
               {})
    _drive(e, play="T1184", pick="T1139", stop_after_pick=True)
    assert e.chars(_cid(e, 0, "T1139"))["power"] == 10000
    assert e.chars(_cid(e, 0, "T001"))["power"] == 2000
    assert e.chars(_cid(e, 0, "T1184"))["power"] == 4000


def test_cip_buff_makes_two_breaks(rules):
    """第2条項の実挙動（breaks_add）: バフを受けた
    T001（パワー2000→6000）がプレイヤーを攻撃すると
    シールドを2枚ブレイクする（3枚→1枚）。"""
    e = _build(rules,
               {"bz": ["T001"], "hand": ["T1184"],
                "mana": ["T001", "T001", "T001", "T001"]},
               {"shield": ["T001", "T001", "T001"]})
    st = _drive(e, play="T1184", pick="T001",
                attack="attack:T001:player")
    assert st["played"] and st["attacked"]
    assert len(e.zlist("shield", 1)) == 1


def test_control_one_break_without_buff(rules):
    """対照: バフの無い T001 の攻撃はシールド
    1枚だけをブレイクする（3枚→2枚）。"""
    e = _build(rules, {"bz": ["T001"]},
               {"shield": ["T001", "T001", "T001"]})
    st = _drive(e, attack="attack:T001:player")
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 2


def test_cip_no_other_creature_no_self_buff(rules):
    """other: true の判別: 他のクリーチャーが
    いなければ、CIP は発生源自身を対象にできず
    パワーは 4000 のまま（other を落とすと自身が
    選べて 8000 になる）。"""
    e = _build(rules,
               {"hand": ["T1184"],
                "mana": ["T001", "T001", "T001", "T001"]},
               {})
    _drive(e, play="T1184", stop_at_attack=True)
    assert _in_zone(e, 0, "bz", "T1184")
    assert e.chars(_cid(e, 0, "T1184"))["power"] == 4000


def test_cip_buff_expires_at_end_of_turn(rules):
    """duration の判別: バフはそのターン限りで、
    次の自分のターンには T001 のパワーは
    2000 に戻っている。"""
    e = _build(rules,
               {"bz": ["T001"], "hand": ["T1184"],
                "mana": ["T001", "T001", "T001", "T001"]},
               {})
    _drive(e, play="T1184", pick="T001", turns=2)
    assert e.chars(_cid(e, 0, "T001"))["power"] == 2000


def _attacker_ready(e, defn="T1184"):
    e.s.cards[_cid(e, 0, defn)].entered_turn = -1


def test_j_change_swaps_with_mana_jokers(rules):
    """第1条項の実挙動: 攻撃時、マナゾーンの
    コスト6以下のジョーカーズ（T068、コスト3）と
    入れ替わり、元のクリーチャーはマナゾーンへ、
    攻撃は入れ替わった T068 で続いてシールドを
    1枚ブレイクする（2枚→1枚）。"""
    e = _build(rules,
               {"bz": ["T1184"], "mana": ["T068", "T001", "T001"]},
               {"shield": ["T001", "T001"]})
    _attacker_ready(e)
    st = _drive(e, attack="attack:T1184:player", swap_pick="T068")
    assert st["attacked"]
    assert _in_zone(e, 0, "bz", "T068")
    assert _in_zone(e, 0, "mana", "T1184")
    assert len(e.zlist("shield", 1)) == 1


def test_j_change_threshold_and_race_filter(rules):
    """閾値・種族フィルタの判別: マナゾーンに
    コスト7のジョーカーズ（T1185）とジョーカーズ
    でない T001 しかいなければ、入れ替えは起きず
    T1184 自身の攻撃でシールドを1枚ブレイクする
    （2枚→1枚）。ドライバは T1185 が選択肢に
    出ればあえて選ぶので、誤って候補になれば
    入れ替わりが起きて落ちる。"""
    e = _build(rules,
               {"bz": ["T1184"], "mana": ["T1185", "T001", "T001"]},
               {"shield": ["T001", "T001"]})
    _attacker_ready(e)
    st = _drive(e, attack="attack:T1184:player", swap_pick="T1185")
    assert st["attacked"]
    assert _in_zone(e, 0, "bz", "T1184")
    assert _in_zone(e, 0, "mana", "T1185")
    assert len(e.zlist("shield", 1)) == 1


def test_j_change_is_optional(rules):
    """任意性の判別: 入れ替えを断れば T1184 自身が
    攻撃し、T068 はマナゾーンに残る。"""
    e = _build(rules,
               {"bz": ["T1184"], "mana": ["T068", "T001", "T001"]},
               {"shield": ["T001", "T001"]})
    _attacker_ready(e)
    st = _drive(e, attack="attack:T1184:player", swap_decline=True)
    assert st["attacked"]
    assert _in_zone(e, 0, "bz", "T1184")
    assert _in_zone(e, 0, "mana", "T068")
    assert len(e.zlist("shield", 1)) == 1
