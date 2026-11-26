"""語彙パイロット第408弾: enters_tapped_rule（ドリフト）。

センサス（rejects 1,924件を取り直し）: pure 1,776件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜407弾）は再提案しない。
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
change_races_until_end_of_turn（pure 1、dm08-017。
種族の「なる」が追加か置換かの公式確認と、呪文の
一括 modify での add_races 付与の検証が要り本弾より
重い）、attack_cancellation（pure 1、dm27-s04。
攻撃の中止＋相手の任意タップ支払いの新機構）、
castle_placed_trigger（pure 1、dm31-024。城を
シールドゾーンに置いた時のイベント照合が未確立）、
bakushin_double（pure 1、dm32-016。モード選択＋
条件つき両方選択の複合）、chain（pure 1、
dmx16-059。連鎖キーワード自体が新機構で、2体目の
登場ドロー誘発も同居）、cancel_spell_effect_on_cast
（pure 1、dm19-s03。メテオバーンの呪文無効化は
新機構）、choose_civ_addition（pure 1、dm25-042。
name を欠く断片行で評価不能）。
後続候補として長く残されてきた **enters_tapped_rule
（pure 1件、multi にも現れない）** を選定した:
3件の静的効果はいずれも登録済み形の owner／フィルタ
違いで、新規語彙は要らない。

対象は dmex11-005 その子供、凶暴につき（火の
クリーチャー / コスト4 / パワー4000 / 種族
ヒューマノイド / チルドレン）。公式テキスト:
「自分のコスト３以下のクリーチャーすべてに
「スピードアタッカー」を与える。（「スピード
アタッカー」を持つクリーチャーは召喚酔いしない）
相手の進化クリーチャーと相手の「スピードアタッカー」を
持つクリーチャーはすべて、タップしてバトルゾーンに
出る。」partial は骨格のみ（types [creature] /
civs [fire] / cost 4 / power 4000 / races
[ヒューマノイド, チルドレン]、mana 1、keywords・
abilities ともに無し）で、未解決は unsupported の
enters_tapped_rule 1件だけ。partial の text は断片
（「タップしてバトルゾーンに出る」）のため
**補完あり: text のみ**（提出形の text は行の公式
テキスト全文）。alias は dmr08s-004 / dmx24-009 /
promoy11-066 の3件で、いずれも rejects に独自行は
無く、identity 実測で canon_id は対象・全 alias
とも dmex11-005、aliases_for = 3件。第408弾時点で
real.yaml / real_akashic.yaml / real_vocab.yaml /
real_zone.yaml / proto.yaml / converted.yaml の
いずれにも登録なし。単面カードで未検証の面は無い。
登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（本弾で実測）。

結論はドリフト（追加語彙なし）。確立形は static 3件:
- 第1条項「自分のコスト３以下のクリーチャーすべてに
  「スピードアタッカー」を与える」は static
  {affects: {zone: bz, owner: you, filter:
  {types: [creature], cost_le: 3}}, mod:
  {grant: [speed_attacker]}}。常在型 static の
  grant [speed_attacker] は登録先例が複数あり
  （自軍クリーチャー全体への付与形）、本件は
  cost_le: 3 のフィルタを足したもの。cost_le は
  FILTER_KEYS の既存キーで defs と schema.py
  （FILTER_KEYS を引く生成）の両側に定義済みを
  確認（第408ラウンドの教訓）。発生源自身は
  コスト4のため対象外。
- 第2条項のうち進化側「相手の進化クリーチャーは
  タップしてバトルゾーンに出る」は static
  {affects: {zone: bz, owner: opp, filter:
  {types: [evolution]}}, mod: {grant:
  [enters_tapped]}}。第384弾・登録済み dm06-001 の
  形（owner: any）の owner を opp に絞ったもの。
- 第2条項のうちスピードアタッカー側は static
  {affects: {zone: bz, owner: opp, filter:
  {types: [creature], keyword: speed_attacker}},
  mod: {grant: [enters_tapped]}}。登録済み
  dmrp06-030 の形（owner: any）の owner を opp に
  絞ったもの。

**既知の制限（実測）: 静的効果の affects 照合は
base=True（印刷特性）で行われるため、他の効果で
付与されたスピードアタッカーは第3件の keyword
フィルタに掛からない（T314 の自己付与で実測し、
本体テストで固定）。dmrp06-030 をはじめ keyword
フィルタを使う登録済み静的効果すべてが共有する
エンジン全体の規約であり、解消は専用ステージ送り
（第398弾と同じ扱い。本弾では扱わない）。** なお
第1条項で自軍に付与したスピードアタッカーは相手の
クリーチャーではないため、この制限と第2条項の
owner: opp は干渉しない。

proto T1176（dmex11-005 型）。判別役は既存 proto を
流用: T001（コスト2バニラ＝第1条項の対象役・自然
マナ役）/ T1090（印刷スピードアタッカー役・火マナ役）/
T1091（バニラ役）/ T1145（進化役）/ T1146（進化元役）/
T314（スピードアタッカー自己付与役＝付与分の制限
確認用）。

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
            "affects": {"zone": "bz", "owner": "you",
                        "filter": {"types": ["creature"],
                                   "cost_le": 3}},
            "mod": {"grant": ["speed_attacker"]}}
TAP_EVO = {"kind": "static",
           "affects": {"zone": "bz", "owner": "opp",
                       "filter": {"types": ["evolution"]}},
           "mod": {"grant": ["enters_tapped"]}}
TAP_SA = {"kind": "static",
          "affects": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"],
                                 "keyword": "speed_attacker"}},
          "mod": {"grant": ["enters_tapped"]}}
FORM = [GRANT_SA, TAP_EVO, TAP_SA]
FULL_TEXT = ("自分のコスト３以下のクリーチャーすべてに「スピードアタッカー」を"
             "与える。（「スピードアタッカー」を持つクリーチャーは召喚酔いしない）\n"
             "相手の進化クリーチャーと相手の「スピードアタッカー」を持つ"
             "クリーチャーはすべて、タップしてバトルゾーンに出る。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1176")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 4 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ヒューマノイド", "チルドレン"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    for a in FORM:
        assert a in d.abilities
    for tid in ("T001", "T1090", "T1091", "T1145", "T1146", "T314"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX408", "name": "その子供、凶暴につき",
                    "types": ["creature"], "civs": ["fire"],
                    "cost": 4, "power": 4000, "mana": 1,
                    "races": ["ヒューマノイド", "チルドレン"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    for a in FORM:
        assert a in d.abilities


def _bad(ability):
    with pytest.raises(DefError):
        parse_card({"id": "TX408B", "name": "x", "types": ["creature"],
                    "civs": ["fire"], "cost": 4, "power": 4000,
                    "abilities": [ability]}, TABLES)


def test_bad_unknown_grant_keyword():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["creature"], "cost_le": 3}},
          "mod": {"grant": ["bogus_kw"]}})


def test_bad_unknown_filter_key():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["creature"],
                                 "cost_le": 3, "bogus_key": 1}},
          "mod": {"grant": ["speed_attacker"]}})


def test_bad_unknown_filter_keyword():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"],
                                 "keyword": "bogus_kw"}},
          "mod": {"grant": ["enters_tapped"]}})


def test_bad_unknown_mod_key():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["evolution"]}},
          "mod": {"bogus_mod": ["enters_tapped"]}})


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
    （第384弾と同形）。"""
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
    ドライバ（第407弾と同型）。"""
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


def test_chars_grant_and_tap_discrimination(rules):
    """特性レベルの判別: 第1条項は自分のコスト3以下に
    だけ speed_attacker を付け（発生源自身はコスト4で
    対象外、相手には付けない）、第3件は相手の印刷
    スピードアタッカーに enters_tapped を付ける
    （相手のバニラには付けない）。"""
    e = _build(rules,
               {"bz": ["T1176", "T001"]},
               {"bz": ["T001", "T1090"]})
    src = _cid(e, "T1176", 0)
    own = _cid(e, "T001", 0)
    opp_v = _cid(e, "T001", 1)
    opp_sa = _cid(e, "T1090", 1)
    assert "speed_attacker" in e.chars(own)["keywords"]
    assert "speed_attacker" not in e.chars(src)["keywords"]
    assert "speed_attacker" not in e.chars(opp_v)["keywords"]
    assert "enters_tapped" in e.chars(opp_sa)["keywords"]
    assert "enters_tapped" not in e.chars(opp_v)["keywords"]
    assert "enters_tapped" not in e.chars(own)["keywords"]


def test_granted_speed_attacker_limitation(rules):
    """既知の制限の固定: 付与されたスピードアタッカー
    （T314 の自己付与）は base 照合のため第3件の
    keyword フィルタに掛からず、enters_tapped は
    付かない。dmrp06-030 等の登録済み keyword
    フィルタ静的効果と共有するエンジン全体の規約
    （第398弾 docs 参照）。"""
    e = _build(rules,
               {"bz": ["T1176"]},
               {"bz": ["T314"]})
    granted = _cid(e, "T314", 1)
    ch = e.chars(granted)
    assert "speed_attacker" in ch["keywords"]   # 付与自体は有効
    assert "enters_tapped" not in ch["keywords"]


def test_own_low_cost_can_attack_on_entry_turn(rules):
    """第1条項の実挙動: 発生源がいれば、自分の
    コスト2バニラ（T001）も出たターンにプレイヤーを
    攻撃できる（付与されたスピードアタッカーで
    召喚酔いしない。シールド1枚減る）。"""
    e = _build(rules,
               {"bz": ["T1176"], "hand": ["T001"],
                "mana": ["T001", "T001"]},
               {"bz": ["T1091"]})
    before = len(e.zlist("shield", 1))
    seen = _drive(e, player=0, play="T001", attack="T001")
    assert seen["played"] and seen["attacked"]
    assert len(e.zlist("shield", 1)) == before - 1


def test_control_without_source_cannot_attack_on_entry_turn(rules):
    """対照: 発生源が無ければ、出たターンのバニラは
    攻撃できない。"""
    e = _build(rules,
               {"hand": ["T001"], "mana": ["T001", "T001"]},
               {"bz": ["T1091"]})
    seen = _drive(e, player=0, play="T001", attack="T001")
    assert seen["played"]
    assert not seen["attacked"]


def test_opponent_evolution_enters_tapped(rules):
    """第2条項（進化側）の実挙動: 相手の進化
    クリーチャー（T1145）は発生源がいる場に
    タップして出る。"""
    e = _build(rules, {"bz": ["T1176"]},
               {"bz": ["T1146"], "hand": ["T1145"],
                "mana": ["T1146", "T001", "T001"]})
    _play(e, 1, "play:T1145", pick="T1146")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1145")].tapped is True


def test_own_evolution_enters_untapped(rules):
    """owner: opp の判別: 自分の進化クリーチャーは
    発生源がいてもタップせずに出る。"""
    e = _build(rules, {"bz": ["T1176", "T1146"], "hand": ["T1145"],
                       "mana": ["T1146", "T001", "T001"]},
               {})
    _play(e, 0, "play:T1145", pick="T1146")
    assert e.s.cards[_zone_card(e, "bz", 0, "T1145")].tapped is False


def test_no_source_evolution_enters_untapped(rules):
    """対照: 発生源が無ければ相手の進化クリーチャーも
    タップせずに出る。"""
    e = _build(rules, {},
               {"bz": ["T1146"], "hand": ["T1145"],
                "mana": ["T1146", "T001", "T001"]})
    _play(e, 1, "play:T1145", pick="T1146")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1145")].tapped is False


def test_opponent_speed_attacker_enters_tapped(rules):
    """第2条項（スピードアタッカー側）の実挙動:
    相手の印刷スピードアタッカー（T1090）は
    タップして出る。"""
    e = _build(rules, {"bz": ["T1176"]},
               {"hand": ["T1090"], "mana": ["T1090", "T1090"]})
    _play(e, 1, "play:T1090")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1090")].tapped is True


def test_opponent_vanilla_enters_untapped(rules):
    """判別: 相手のバニラ（T1091）はどちらのフィルタ
    にも掛からず、タップせずに出る。"""
    e = _build(rules, {"bz": ["T1176"]},
               {"hand": ["T1091"], "mana": ["T1091", "T1091"]})
    _play(e, 1, "play:T1091")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1091")].tapped is False


def test_own_speed_attacker_enters_untapped(rules):
    """owner: opp の判別: 自分のスピードアタッカーは
    発生源がいてもタップせずに出る。"""
    e = _build(rules, {"bz": ["T1176"], "hand": ["T1090"],
                       "mana": ["T1090", "T1090"]},
               {})
    _play(e, 0, "play:T1090")
    assert e.s.cards[_zone_card(e, "bz", 0, "T1090")].tapped is False
