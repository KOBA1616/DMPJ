"""語彙パイロット第409弾: enters_tapped_grant（ドリフト）。

センサス（rejects 1,923件を取り直し）: pure 1,775件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜408弾）は再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021、
battle_opponent_reference の残り1件 dmr01-049、
untap_restriction の残り2件（dm26rp1-td004 /
dmx15-011、形が異なると判定済み）、cast_limit_
once_per_turn の multi 2件（dm26ex2-pr006 /
dm26ex4-cho031、他の gaps を併せ持つ）、
summoning_attack_rule の残り1件 dmex07-s01
（partial が素で条項未構築）、entered_turn_attack の
残り1件 dmbd11-d05（J・O・E 等が未構築）は先行弾の
評価を覆す根拠が無く再提案しない。
destroyed_this_turn_condition と count_cards_drawn_
this_turn は次点のまま残す。distinct_civ_count
（dmx19-s45、3条項の複合）は後続候補のまま残す。
本弾で個別に評価して見送った候補:
trigger_when_drawn（pure 1、dm22rp2x-tr4。手札で
引いた時に誘発する手札ゾーン誘発＋表向きにする
機構が未確立）、turn_wide_trigger_grant（pure 1、
dmr05-052。呪文から「このターン」持続の攻撃時
誘発を付与する形は、第401弾の常在型 static gain
とは発生源が違い未検証）、attack_trigger_grant
（pure 1、promoy14-074。付与した攻撃時誘発の効果が
攻撃クリーチャー自身を修整＋バトル中破壊されない
複合）、next_shield_grant（pure 1、dm39-007。
「次に手札に加えるシールド」への将来分付与で、
第392弾の既存シールドへの dynamic modify とは
機構が違う）、s_trigger_grant_all（pure 1、
dmr16s-s01。セイバー付与も partial に未構築で
将来シールド付与と同居する複合）、battle_win_
grant（pure 1、dmc67-016。他のクリーチャーを
特定のバトルに勝たせる形は無く、win_all_battles は
自身の常在型のみ）、no_leave_except_destroy
（pure 1、promoy22-spd1001。no_leave の破壊例外
指定＋自分のターン中条件の形が未確立）、
highest_power_condition（pure 1、dm26rp1-021。
partial に be_blocked deny の試行が同居し
ハイパー化／Zラッシュ条項も含む複合で、本 gap
単独では登録形が定まらない）、same_race_grant
（dm25-011）／same_race_condition（dm25-018）
（いずれも pure 1。「このクリーチャーと同じ種族」を
動的に指すフィルタが無く、両行ともゴッド・リンク
条項を持つ）、summoned_or_cast_this_turn_condition
（dmrp15-s07）／survivor_grant（dm23ex2-103）
（いずれも pure 1。partial の無い素行で評価不能）。
範囲内・最小の **enters_tapped_grant（pure 1件、
multi にも現れない）** を選定した: 未解決条項は
「相手のクリーチャーはタップして出る」だけで、
その形は第340弾・登録済み dmc52-007 の登録形と
完全一致する。

対象は dm26ex3-010 永遠のリュウセイ・カイザー
（火のクリーチャー / コスト8 / パワー8000 / 種族
レッド・コマンド・ドラゴン / ハンター）。公式
テキスト: 「W・ブレイカー / 自分のクリーチャー
すべてに「スピードアタッカー」を与える。/
相手のクリーチャーはタップして出る。/ 相手の、
クリーチャーの能力または呪文によって、この
クリーチャーが自分の手札から捨てられる時、
墓地に置くかわりに出してもよい。」partial は
骨格完備（mana 1、keywords [double_breaker]）で、
abilities には第1条項の static が構築済み。
未解決は unsupported の enters_tapped_grant
1件だけ。**第3条項（手札から捨てられる時の置換）は
partial に未構築だが、同一文面の登録済み
dm26ex3-dcr005 蒼神龍アナザー・ワールド
（同セット）の登録形と完全一致する形で表せる
ことを本弾で検証した**（行の gaps が
enters_tapped_grant のみなのはこのため）。
partial の text は行の公式テキスト全文と一致
するため**補完なし**。alias は dm23bd4-015 /
dm26sd1-j002f / dmbd05-003 / dmbd09-006 /
dmd13-009 / dmd20-016 / dmex15-a029 /
dmex17-cho19 / dmr02-s03 / dmx22b-094 /
promoy15-051 の11件で、いずれも rejects に
独自行は無く、identity 実測で canon_id は対象・
全 alias とも dm26ex3-010、aliases_for = 11件。
第409弾時点で real.yaml / real_akashic.yaml /
real_vocab.yaml / real_zone.yaml / proto.yaml /
converted.yaml のいずれにも登録なし。単面
カードで未検証の面は無い。登録ブロッカーの
確認（第375弾の教訓）: rule_convert.split
（対象行）は (['double_breaker'], 条項テキスト,
[SA付与 static]) を返し、part[2] の定型所有は
第1条項の static 1件のみ。提出形の当該 static は
part[2] と完全一致させるため、merge_split の
完全一致 dedupe で二重付着は起きない見込み
（ラウンド444で登録後の abilities 件数を
必ず照合すること）。

結論はドリフト（追加語彙なし）。確立形は
abilities 3件（文面の条項順）:
- 第1条項「自分のクリーチャーすべてに
  「スピードアタッカー」を与える」は partial
  構築済みの static {affects: {owner: you,
  filter: {types: [creature]}}, mod:
  {grant: [speed_attacker]}}。zone を欠く形は
  登録先例 dmbd05-006 / dmbd09-007 / dm23-015 と
  同形（発生源自身も「自分のクリーチャー」に
  含まれる。本弾で実挙動判別済み）。
- 第2条項「相手のクリーチャーはタップして出る」は
  static {affects: {zone: bz, owner: opp,
  filter: {types: [creature]}}, mod:
  {grant: [enters_tapped]}}。登録済み
  dmc52-007（第340弾）の登録形と完全一致
  （第339弾の grant [enters_tapped] 確立形）。
  keyword フィルタを含まないため、相手の
  クリーチャーはすべて（進化・付与 SA を含む）
  対象になる。第398弾の base 照合の制限は
  本形には及ばない。
- 第3条項は replace {zone: hand, optional: true,
  when: {event: move, from: hand, to: graveyard,
  reason: discard, subject: self, by: opp},
  instead: [{op: move, select: {ref: self,
  count: 1}, to: bz, reason: put}]}。登録済み
  dm26ex3-dcr005（同一文面）の登録形と完全一致
  （by: opp は第40弾で確立、dm25ex2-079 も同形）。
  zone: hand 宣言の置換のため、第386弾の
  発生源走査制限（bz 起点のみ）は及ばない。

proto T1177（dm26ex3-010 型）。判別役は既存
proto を流用: T001（バニラ役・自然マナ役）/
T1090（印刷スピードアタッカー役・火マナ役）/
T1091（バニラ役）/ T1145・T1146（進化・進化元役）/
T116（同一文面の捨て置換役）/ T117（相手の手札を
捨てさせる呪文役）/ T118（自分の手札を捨てる
呪文役）/ T008（闇マナ役）。

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

GRANT_SA = {"kind": "static",
            "affects": {"owner": "you",
                        "filter": {"types": ["creature"]}},
            "mod": {"grant": ["speed_attacker"]}}
TAP_ALL = {"kind": "static",
           "affects": {"zone": "bz", "owner": "opp",
                       "filter": {"types": ["creature"]}},
           "mod": {"grant": ["enters_tapped"]}}
MADNESS = {"kind": "replace", "zone": "hand", "optional": True,
           "when": {"event": "move", "from": "hand",
                    "to": "graveyard", "reason": "discard",
                    "subject": "self", "by": "opp"},
           "instead": [{"op": "move",
                        "select": {"ref": "self", "count": 1},
                        "to": "bz", "reason": "put"}]}
FORM = [GRANT_SA, TAP_ALL, MADNESS]
FULL_TEXT = ("W・ブレイカー\n"
             "自分のクリーチャーすべてに「スピードアタッカー」を与える。\n"
             "相手のクリーチャーはタップして出る。\n"
             "相手の、クリーチャーの能力または呪文によって、このクリーチャーが"
             "自分の手札から捨てられる時、墓地に置くかわりに出してもよい。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1177")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 8 and c["power"] == 8000 and c["mana"] == 1
    assert c["races"] == ["レッド・コマンド・ドラゴン", "ハンター"]
    assert c["keywords"] == ["double_breaker"]
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    for a in FORM:
        assert a in d.abilities
    for tid in ("T001", "T008", "T1090", "T1091", "T1145",
                "T1146", "T116", "T117", "T118"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX409", "name": "永遠のリュウセイ・カイザー",
                    "types": ["creature"], "civs": ["fire"],
                    "cost": 8, "power": 8000, "mana": 1,
                    "races": ["レッド・コマンド・ドラゴン", "ハンター"],
                    "keywords": ["double_breaker"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    for a in FORM:
        assert a in d.abilities
    # parse 後の double_breaker 派生 static を除き3件
    assert len(d.abilities) == 4


def _bad(ability):
    with pytest.raises(DefError):
        parse_card({"id": "TX409B", "name": "x", "types": ["creature"],
                    "civs": ["fire"], "cost": 8, "power": 8000,
                    "abilities": [ability]}, TABLES)


def test_bad_unknown_grant_keyword():
    _bad({"kind": "static",
          "affects": {"owner": "you",
                      "filter": {"types": ["creature"]}},
          "mod": {"grant": ["bogus_kw"]}})


def test_bad_unknown_filter_key():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"],
                                 "bogus_key": 1}},
          "mod": {"grant": ["enters_tapped"]}})


def test_bad_unknown_mod_key():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"]}},
          "mod": {"bogus_mod": ["enters_tapped"]}})


def test_bad_by_value():
    _bad({"kind": "replace", "zone": "hand", "optional": True,
          "when": {"event": "move", "from": "hand",
                   "to": "graveyard", "reason": "discard",
                   "subject": "self", "by": "bogus"},
          "instead": [{"op": "move",
                       "select": {"ref": "self", "count": 1},
                       "to": "bz", "reason": "put"}]})


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, defn, p):
    return next(c for c in e.bz_tops(p) if e.cdef(c).id == defn)


def _zone_card(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p)
                if e.s.cards[c].defn == defn)


def _play(e, player, play_key, pick=None, limit=600):
    """player の main で play_key を使い、対象カードが
    バトルゾーンに出るまで進める汎用ドライバ
    （第408弾と同形）。"""
    defn = play_key.split(":", 1)[1]
    for _ in range(limit):
        if any(e.s.cards[c].defn == defn
               for c in e.zlist("bz", player)):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == player \
                and play_key in keys:
            e.answer([keys.index(play_key)])
            continue
        if pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("play never happened")


def _drive(e, player, play=None, attack=None):
    """player の最初の main のターンだけを対象に進める
    ドライバ（第408弾と同型）。"""
    seen = {"attack_keys": [], "played": False,
            "attacked": False, "target_turn": None}
    for _ in range(600):
        if seen["target_turn"] is not None \
                and e.s.turn > seen["target_turn"] + 1:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        pl = d.get("player")
        if kind in ("charge", "main", "attack") \
                and pl == player and seen["target_turn"] is None:
            seen["target_turn"] = e.s.turn
        if kind == "main" and pl == player and play \
                and not seen["played"]:
            hit = [i for i, k in enumerate(keys)
                   if k == f"play:{play}"]
            if hit:
                seen["played"] = True
                seen["target_turn"] = e.s.turn
                e.answer([hit[0]])
                continue
        if kind == "attack" and pl == player \
                and e.s.turn == seen["target_turn"]:
            seen["attack_keys"].extend(keys)
            hit = [i for i, k in enumerate(keys)
                   if attack and k == f"attack:{attack}:player"]
            if hit and not seen["attacked"]:
                seen["attacked"] = True
                e.answer([hit[0]])
                continue
        if kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return seen


def test_chars_discrimination(rules):
    """特性レベルの判別: 第1条項は自分のクリーチャー
    すべて（発生源自身を含む）に speed_attacker を
    付け、第2条項は相手のクリーチャーすべて
    （バニラ・印刷スピードアタッカーとも）に
    enters_tapped を付ける（自分のクリーチャーには
    付けない）。"""
    e = _build(rules,
               {"bz": ["T1177", "T001"]},
               {"bz": ["T1091", "T1090"]})
    src = _cid(e, "T1177", 0)
    own = _cid(e, "T001", 0)
    opp_v = _cid(e, "T1091", 1)
    opp_sa = _cid(e, "T1090", 1)
    assert "speed_attacker" in e.chars(src)["keywords"]
    assert "speed_attacker" in e.chars(own)["keywords"]
    assert "enters_tapped" in e.chars(opp_v)["keywords"]
    assert "enters_tapped" in e.chars(opp_sa)["keywords"]
    assert "enters_tapped" not in e.chars(own)["keywords"]
    assert "enters_tapped" not in e.chars(src)["keywords"]


def test_opponent_vanilla_enters_tapped(rules):
    """第2条項の実挙動: 相手のバニラ（T1091）は
    発生源がいる場にタップして出る。"""
    e = _build(rules, {"bz": ["T1177"]},
               {"hand": ["T1091"], "mana": ["T1091", "T1091"]})
    _play(e, 1, "play:T1091")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1091")].tapped is True


def test_opponent_evolution_enters_tapped(rules):
    """第2条項は進化クリーチャーにも及ぶ: 相手の
    進化（T1145）もタップして出る（第384弾の
    エンジン修正で進化の重ね置きでもタップ入りが
    維持される）。"""
    e = _build(rules, {"bz": ["T1177"]},
               {"bz": ["T1146"], "hand": ["T1145"],
                "mana": ["T1146", "T001", "T001"]})
    _play(e, 1, "play:T1145", pick="T1146")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1145")].tapped is True


def test_own_creature_enters_untapped(rules):
    """owner: opp の判別: 自分のクリーチャーは
    発生源がいてもタップせずに出る。"""
    e = _build(rules, {"bz": ["T1177"], "hand": ["T1091"],
                       "mana": ["T1091", "T1091"]},
               {})
    _play(e, 0, "play:T1091")
    assert e.s.cards[_zone_card(e, "bz", 0, "T1091")].tapped is False


def test_no_source_opponent_enters_untapped(rules):
    """対照: 発生源が無ければ相手のクリーチャーも
    タップせずに出る。"""
    e = _build(rules, {},
               {"hand": ["T1091"], "mana": ["T1091", "T1091"]})
    _play(e, 1, "play:T1091")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1091")].tapped is False


def test_granted_speed_attacker_can_attack_on_entry_turn(rules):
    """第1条項の実挙動: 発生源がいれば、自分の
    バニラ（T001）も出たターンにプレイヤーを
    攻撃できる（シールド1枚減る）。"""
    e = _build(rules,
               {"bz": ["T1177"], "hand": ["T001"],
                "mana": ["T001", "T001"]},
               {"bz": ["T1091"]})
    before = len(e.zlist("shield", 1))
    seen = _drive(e, player=0, play="T001", attack="T001")
    assert seen["played"] and seen["attacked"]
    assert len(e.zlist("shield", 1)) == before - 1


def test_no_source_vanilla_cannot_attack_on_entry_turn(rules):
    """対照: 発生源が無ければ、出たターンのバニラは
    攻撃できない。"""
    e = _build(rules,
               {"hand": ["T001"], "mana": ["T001", "T001"]},
               {"bz": ["T1091"]})
    seen = _drive(e, player=0, play="T001", attack="T001")
    assert seen["played"]
    assert not seen["attacked"]


def _settle(e, done, drive, max_steps=300):
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if drive(e, d, keys):
            continue
        e.answer([keys.index("pass")] if "pass" in keys
                 else list(range(d["min"])))
    return done()


def _discard_drive(caster, victim, accept=True):
    """第40弾と同型の駆動: player 0 が caster を唱え、
    victim を捨てさせ、置換の諾否を選ぶ。"""
    st = {"played": False}

    def drive(e, d, keys):
        if d["kind"] == "main" and d["player"] == 0 \
                and not st["played"]:
            k = f"play:{caster}"
            if k in keys:
                st["played"] = True
                e.answer([keys.index(k)])
                return True
        if d["kind"] == "pay_mana" and d["player"] == 0:
            e.answer(list(range(d["min"])))
            return True
        if d["kind"] == "choose_replacement":
            if accept:
                hit = [i for i, k in enumerate(keys)
                       if "replace:" in k]
                if hit:
                    e.answer([hit[0]])
                    return True
            else:
                if "pass" in keys:
                    e.answer([keys.index("pass")])
                    return True
                hit = [i for i, k in enumerate(keys)
                       if "replace:" not in k]
                if hit:
                    e.answer([hit[0]])
                    return True
        if d["kind"] == "choose_cards":
            hit = [i for i, k in enumerate(keys) if victim in k]
            if hit:
                e.answer([hit[0]])
                return True
        return False
    return drive


def test_madness_replace_puts_into_bz(rules):
    """第3条項の実挙動: 相手の呪文（T117）で
    捨てられる時、置換を選べば墓地ではなく
    バトルゾーンに出る（by: opp、第40弾と同型）。"""
    e = _build(rules, {"hand": ["T117"], "mana": ["T008"] * 4},
               {"hand": ["T1177"]})
    v = _zone_card(e, "hand", 1, "T1177")
    assert _settle(e, lambda: e.s.cards[v].zone == "bz",
                   _discard_drive("T117", "T1177", True))
    assert v in e.zlist("bz", 1)
    assert v not in e.zlist("graveyard", 1)


def test_madness_replace_is_optional(rules):
    """第3条項は任意: 置換を断れば墓地に置かれる。"""
    e = _build(rules, {"hand": ["T117"], "mana": ["T008"] * 4},
               {"hand": ["T1177"]})
    v = _zone_card(e, "hand", 1, "T1177")
    assert _settle(e, lambda: e.s.cards[v].zone == "graveyard",
                   _discard_drive("T117", "T1177", False))
    assert v not in e.zlist("bz", 1)


def test_madness_not_triggered_by_own_spell(rules):
    """by: opp の判別: 自分の呪文（T118）で自分の
    手札から捨てる時は置換が発火せず、墓地に行く。"""
    e = _build(rules,
               {"hand": ["T118", "T1177"], "mana": ["T008"] * 2},
               {})
    v = _zone_card(e, "hand", 0, "T1177")
    assert _settle(e, lambda: e.s.cards[v].zone == "graveyard",
                   _discard_drive("T118", "T1177", True))
    assert v not in e.zlist("bz", 0)
