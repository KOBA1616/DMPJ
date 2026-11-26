"""語彙パイロット第407弾: summoning_attack_rule（ドリフト）。

センサス（rejects 1,926件を取り直し）: pure 1,778件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜406弾）は再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021、
battle_opponent_reference の残り1件 dmr01-049、
untap_restriction の残り2件（dm26rp1-td004 /
dmx15-011）、cast_limit_once_per_turn の multi 2件
（dm26ex2-pr006 / dm26ex4-cho031）は先行弾の評価を
覆す根拠が無く再提案しない。destroyed_this_turn_
condition と count_cards_drawn_this_turn は次点の
まま残す。enters_tapped_rule（dmex11-005、静的効果
3件）と distinct_civ_count（3条項の複合）は後続候補
のまま残す。本弾で個別に評価して見送った候補:
s_trigger_restriction（pure 1、dmex08-036。発生源の
タップ状態を条件にする static if が未確立＝第403弾の
s_trigger_lock 却下と同根）、conditional_tapped_state
（pure 1、dmrp01-008。自分のタップ／アンタップ状態で
切り替わる静的効果2件で同根）、next_spell_cost_
reduction（pure 3。「次に唱える呪文」への1回限りの
コスト付与の確立形が無い）、civ_blocker（pure 2。
文明を指定するブロック制限の範囲形が未確立で、
その文明とのバトル敗北時の置換も同居）、look_reorder
（pure 2。山札の上を見て好きな順序で戻す op が未確立
で look 系の変種は軒並み gaps に残る）、eternal_omega
（pure 1、dmx15-s01。各文明1体ずつの破壊誘発が
partial に未構築の複合）、genius_sympathy /
triple_sympathy（シンパシー変種だが勝敗条件／
バトルさせる条項が未構築で単一条項でない）、
draw_up_to（pure 2。「N枚まで」の枚数選択が未確立で
両行とも他条項が未構築）、martial_touch（pure 1。
戻すことを条件に g 能力を使う束縛形が未検証で
partial が素）、koorin（pure 1、dmd12-012。ターン
終了時＋自分のタップ状態条件＋山札から出す複合）。
範囲内・最小の **summoning_attack_rule（pure 2件）**
を選定した。

対象は dmex02-011 超絶特Q ダンガンテイオー（ゼロの
クリーチャー / コスト8 / パワー8000 / 種族
ジョーカーズ）。partial は骨格完備で、構築済みは
keywords [double_breaker]、未解決は unsupported の
summoning_attack_rule 1件だけ。partial の text は
行の公式テキスト全文と一致するため**補完なし**。
alias は promoy16-008 の1件で、identity 実測で
canon_id は対象・alias とも dmex02-011。ただし
**promoy16-008 には gap entered_turn_attack での
独自行がある**（同カード・同義の別版テキスト。
entered_turn_attack は pure 2件で、もう1件は
dmbd11-d05 バーバーパパ＝別カード。その条項は
第261弾の self 型 player_rush そのものだが、
J・O・E と攻撃時誘発のバトル条項が未構築で本弾では
登録形が定まらない）。第407弾時点で dmex02-011 /
promoy16-008 は real.yaml / real_akashic.yaml /
real_vocab.yaml / real_zone.yaml / proto.yaml /
converted.yaml のいずれにも登録なし。単面カードで
未検証の面は無い。

ファミリーの残り1件 dmex07-s01 ガンバトラーG７ は
対象外: partial が素で、第1条項（ジョーカーズ4体
以上での一律コスト軽減）と第3条項（出た時のパワー
+7000 modify）が未構築のまま同居し、本弾では組として
検証しない。第4条項は本弾の付与形の種族フィルタ版。
ファミリーは解消しない。

結論はドリフト（追加語彙なし）:
- 条項「自分のクリーチャーは、バトルゾーンに出た
  ターン、プレイヤーを攻撃できる」の確立形は
  static {affects: {zone: bz, owner: you, filter:
  {types: [creature], entered_this_turn: true}},
  mod: {player_rush: true}} の1件。第261弾の mod
  player_rush（出たターンにプレイヤーだけは攻撃
  できる。self 形は登録済み promoy17-sp4d01 =
  static {affects: self, if: {exists: {ref: self,
  filter: {entered_this_turn: true}}}, mod:
  {player_rush: true}}）を自軍全体への付与に
  一般化したもの。player_rush の特性は出たターンに
  しか参照されない（combat._attack_options の
  rush 分岐）ため、entered_this_turn フィルタは
  文面の範囲の明示でもある。クリーチャーへの攻撃は
  解放しない（player_rush の意味論そのもの）。
- 条項「相手のクリーチャーは、バトルゾーンに出た
  ターン、プレイヤーを攻撃できない」の確立形は
  static {affects: {zone: bz, owner: opp, filter:
  {types: [creature], entered_this_turn: true}},
  mod: {deny: [attack_player]}} の1件。第362弾の
  登録先例の deny 形（entered_this_turn フィルタ＋
  deny）を attack_player のみに絞ったもの
  （文面はプレイヤー攻撃のみを禁じ、クリーチャー
  への攻撃は奪わない）。
- player_rush は MOD_KEYS の既存キーで defs と
  schema.py（生成済み card.schema.json）の両側に
  定義済み、entered_this_turn も FILTER_KEYS の
  既存キーで両側に定義済み（第408ラウンドの教訓）。

第398弾の base 照合の制限は本 deny には及ばない:
本 deny のフィルタは keyword を含まないため、他の
効果で付与されたスピードアタッカー（T314 の自己
付与）にも deny が掛かることを実挙動で判別した
（第398弾の keyword フィルタ形との対照）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['double_breaker'], 条項テキスト,
[]) を返し、part[2] の定型所有は空＝ブロッカー無し
（本弾で実測）。

proto T1175（dmex02-011 型）。判別役は既存 proto を
流用: T1090（スピードアタッカー役・火マナ役）/
T1091（通常クリーチャー役）/ T314（スピード
アタッカー自己付与役）/ T001（通常クリーチャー役）。

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

GRANT = {"kind": "static",
         "affects": {"zone": "bz", "owner": "you",
                     "filter": {"types": ["creature"],
                                "entered_this_turn": True}},
         "mod": {"player_rush": True}}
DENY = {"kind": "static",
        "affects": {"zone": "bz", "owner": "opp",
                    "filter": {"types": ["creature"],
                               "entered_this_turn": True}},
        "mod": {"deny": ["attack_player"]}}
FORM = [GRANT, DENY]
FULL_TEXT = ("W・ブレイカー（このクリーチャーはシールドを２つブレイクする）\n"
             "自分のクリーチャーは、バトルゾーンに出たターン、プレイヤーを攻撃できる。\n"
             "相手のクリーチャーは、バトルゾーンに出たターン、プレイヤーを攻撃できない。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1175")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"] and c["civs"] == ["zero"]
    assert c["cost"] == 8 and c["power"] == 8000 and c["mana"] == 1
    assert c["races"] == ["ジョーカーズ"]
    assert c["keywords"] == ["double_breaker"]
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    for a in FORM:
        assert a in d.abilities
    for tid in ("T1090", "T1091", "T314", "T001"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX407", "name": "超絶特Q ダンガンテイオー",
                    "types": ["creature"], "civs": ["zero"],
                    "cost": 8, "power": 8000, "mana": 1,
                    "races": ["ジョーカーズ"],
                    "keywords": ["double_breaker"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    for a in FORM:
        assert a in d.abilities


def _bad(ability):
    with pytest.raises(DefError):
        parse_card({"id": "TX407B", "name": "x", "types": ["creature"],
                    "civs": ["zero"], "cost": 8, "power": 8000,
                    "abilities": [ability]}, TABLES)


def test_bad_player_rush_not_true():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["creature"],
                                 "entered_this_turn": True}},
          "mod": {"player_rush": False}})


def test_bad_unknown_mod_key():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["creature"],
                                 "entered_this_turn": True}},
          "mod": {"bogus_mod": True}})


def test_bad_unknown_filter_key():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"],
                                 "entered_this_turn": True,
                                 "bogus_key": 1}},
          "mod": {"deny": ["attack_player"]}})


def test_bad_unknown_deny_action():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"],
                                 "entered_this_turn": True}},
          "mod": {"deny": ["fly"]}})


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, defn, p):
    return next(c for c in e.bz_tops(p) if e.cdef(c).id == defn)


def _drive(e, player, play=None, attack=None):
    """player の最初の main のターンだけを対象に進める
    ドライバ（第398弾と同型）。"""
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


def test_own_vanilla_entered_this_turn_can_attack_player(rules):
    """付与の判別: 発生源がいれば、通常クリーチャーでも
    出たターンにプレイヤーを攻撃できる（シールド1枚
    減る）。クリーチャーへの攻撃は解放されない。"""
    e = _build(rules,
               {"bz": ["T1175"], "hand": ["T1091"],
                "mana": ["T1091", "T1091"]},
               {"bz": ["T1091"]})
    before = len(e.zlist("shield", 1))
    seen = _drive(e, player=0, play="T1091", attack="T1091")
    assert seen["played"] and seen["attacked"]
    assert len(e.zlist("shield", 1)) == before - 1
    assert not [k for k in seen["attack_keys"]
                if k.startswith("attack:T1091:T")]


def test_control_without_source_vanilla_cannot_attack(rules):
    """対照: 発生源が無ければ、出たターンの通常
    クリーチャーは攻撃できない。"""
    e = _build(rules,
               {"hand": ["T1091"], "mana": ["T1091", "T1091"]},
               {"bz": ["T1091"]})
    seen = _drive(e, player=0, play="T1091", attack="T1091")
    assert seen["played"]
    assert not seen["attacked"]
    assert not [k for k in seen["attack_keys"]
                if k.startswith("attack:T1091:")]


def test_opp_speed_attacker_entered_this_turn_cannot_attack_player(rules):
    """deny の判別: 相手のスピードアタッカーも、出た
    ターンにはプレイヤーを攻撃できない（攻撃先の
    クリーチャーがいない配置では攻撃自体が提示
    されない）。"""
    e = _build(rules,
               {"bz": ["T1175", "T1091"]},
               {"hand": ["T1090"], "mana": ["T1090", "T1090"]})
    shields = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, play="T1090", attack="T1090")
    assert seen["played"]
    assert not seen["attacked"]
    assert not [k for k in seen["attack_keys"]
                if k.startswith("attack:T1090:")]
    assert not e.s.cards[_cid(e, "T1090", 1)].tapped
    assert len(e.zlist("shield", 0)) == shields


def test_opp_speed_attacker_from_previous_turn_can_attack(rules):
    """前ターンからいる相手のスピードアタッカーには
    deny が及ばず、発生源がいてもプレイヤーを攻撃
    できる（entered_this_turn の判別）。"""
    e = _build(rules,
               {"bz": ["T1175"]},
               {"bz": ["T1090"]})
    before = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, attack="T1090")
    assert seen["attacked"]
    assert len(e.zlist("shield", 0)) == before - 1


def test_chars_grant_and_deny_discrimination(rules):
    """特性レベルの判別: 出たターンの自軍クリーチャー
    （発生源自身を含む）には player_rush が付き、
    出たターンの相手クリーチャーには attack_player
    の deny だけが付く（attack_creature は奪わない）。
    前ターンからいるものにはどちらも付かない。"""
    e = _build(rules,
               {"bz": ["T1175", "T1091"]},
               {"bz": ["T1090"]})
    src = _cid(e, "T1175", 0)
    own = _cid(e, "T1091", 0)
    opp = _cid(e, "T1090", 1)
    for c in (src, own, opp):
        e.s.mut_card(c).entered_turn = e.s.turn
    assert e.chars(own)["player_rush"] is True
    assert e.chars(src)["player_rush"] is True   # 発生源自身も対象
    deny = e.chars(opp)["deny"]
    assert "attack_player" in deny
    assert "attack_creature" not in deny
    assert e.chars(opp)["player_rush"] is False  # 付与は自軍だけ
    for c in (own, opp):
        e.s.mut_card(c).entered_turn = e.s.turn - 1
    assert e.chars(own)["player_rush"] is False
    assert "attack_player" not in e.chars(opp)["deny"]


def test_attack_options_source_and_granted_sa(rules):
    """攻撃選択肢レベルの判別: (1) 発生源自身も、出た
    ターンはプレイヤーへの攻撃だけが提示される
    （クリーチャーへの攻撃は提示されない）。
    (2) 付与されたスピードアタッカー（T314）にも
    deny が掛かる（フィルタに keyword を含まない
    ため第398弾の base 照合の制限は及ばない）:
    プレイヤーへの攻撃は提示されず、タップしている
    クリーチャーへの攻撃は提示される。"""
    e = _build(rules,
               {"bz": ["T1175", "T1091"]},
               {"bz": ["T314"]})
    src = _cid(e, "T1175", 0)
    own = _cid(e, "T1091", 0)
    granted = _cid(e, "T314", 1)
    for c in (src, own, granted):
        e.s.mut_card(c).entered_turn = e.s.turn
    ch = e.chars(granted)
    assert "speed_attacker" in ch["keywords"]   # 付与自体は有効
    assert "attack_player" in ch["deny"]
    e.s.mut_card(own).tapped = True             # 相手の攻撃先用
    keys1 = [o["key"] for o in e._attack_options(1)]
    assert "attack:T314:player" not in keys1
    assert "attack:T314:T1091" in keys1         # クリーチャー攻撃は可
    keys0 = [o["key"] for o in e._attack_options(0)]
    assert "attack:T1175:player" in keys0
    assert not [k for k in keys0 if k.startswith("attack:T1175:T")]
