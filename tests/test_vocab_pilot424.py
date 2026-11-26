"""語彙パイロット第424弾: entry_turn_attack（ドリフト）。

センサス（rejects 1,908件を取り直し）: pure 1,761件
（994ファミリー）/ multi の gap 出現 268件 /
空 gaps 18件。pure の大半は範囲外（gr_summon 147 /
aura 108＝未承認 / hyperdimensional_zone 105 /
dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜423弾）は原則として再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021、
battle_opponent_reference の残り1件 dmr01-049、
untap_restriction の残り2件（dm26rp1-td004 /
dmx15-011）、does_not_untap の残り1件 dm25ex2-031、
cast_limit_once_per_turn の multi 2件、
summoning_attack_rule の残り1件 dmex07-s01
（partial が素）、entered_turn_attack の残り1件
dmbd11-d05（J・O・E 等が未構築）、madness の残り1件
dmx26-028（CIP が look/reorder 系の未確立機構）は
先行弾の評価を覆す根拠が無く再提案しない。
destroyed_this_turn_condition と count_cards_drawn_
this_turn は次点のまま、distinct_civ_count は後続
候補のまま、first_time_tap（pure 2、第410弾で記録）
は将来の新規語彙候補として残置。本弾で個別に評価
して見送った候補: dmrp09-011（シンパシー＋攻撃時
誘発の複合）、dmr15-005 battle_lose（複合）、
dm20-025（敗者不破壊の置換形が未確認）、
dmrp03-042（任意アンタップの組み合わせ未検証）、
dmrp15-s07（素行・複合）、dm25rp3-020 /
dm26rp2-tr007（複合）、dm26sd1-g004 first_battle_win
（first_time 付与形が未検証、第423弾と同根）、
dmx08-019（ガチンコ・ジャッジ未確立）、
dmrp02-029（複合）、dmd11-006（表向きシールドの
照合形が未確立）。

範囲内・最小の **entry_turn_attack（pure 1件、
multi にも現れない）** を選定した。本候補は第392弾で
「召喚酔いのプレイヤー限定バイパスの確立形が未確認」
として見送られたが、その評価は登録先例の見落とし
だった（第410・411・418・420・422弾と同じ型の覆し）:
- 第261弾の mod **player_rush**（出たターンに
  プレイヤーだけは攻撃できる）がそのバイパスで、
  登録済み **promoy17-sp4d01** が本件と同一文面
  「このクリーチャーは、バトルゾーンに出たターンの間、
  相手プレイヤーを攻撃できる。」を self 形
  static {affects: self, if: {exists: {ref: self,
  filter: {entered_this_turn: true}}}, mod:
  {player_rush: true}} で登録済み（本弾で converted の
  登録形を直接照合）。第407弾もこの self 形を明記し、
  自軍全体付与への一般化を登録した。player_rush は
  MOD_KEYS の既存キーで defs と schema.py の両側に
  定義済み、entered_this_turn も FILTER_KEYS の既存
  キーで両側に定義済み（ラウンド408の教訓で確認）。
  player_rush の特性は combat の rush 分岐でのみ
  参照されるため、出たターン以外に効かない。
- クリーチャー面 第1条項「W・ブレイカー」は
  keywords [double_breaker]。
- 呪文面「ジョーカーズを１枚、自分の墓地から
  マナゾーンに置く」は spell [move {select:
  {zone: graveyard, owner: you, filter:
  {race_has: ジョーカーズ}, count: 1}, to: mana,
  reason: put}]（墓地→マナの move は登録済み
  dm23bd5-042 の呪文形。本件は必須1枚で up_to 無し、
  種別指定が無いため types フィルタ無し。墓地 select
  の race_has フィルタは登録先例あり）。

対象は dmbd07-a-006 ガンバＧ/ガガン・ガン・ガガン
（ツインパクト。クリーチャー面: ゼロ / コスト6 /
パワー6000 / 種族 ジョーカーズ。呪文面: コスト2）。
partial はクリーチャー面の骨格のみ（name は
ガンバＧ、text は第2条項の断片、keywords・
abilities・faces 無し）。**補完あり: faces 構造＋
text＋keywords**（両面とも公式全文。最上位 text は
両面を「 ／ 」で連結。面名は公式名を / で分けた
ガンバＧ ／ ガガン・ガン・ガガン）。呪文面の文明は
公式データで空文字だが、同 product（bd07）の
ツインパクトで明示される場合はクリーチャー面と同一
（dmbd07-b-010）であり、空文字は欠落と判断して
両面とも zero とする。alias は dmsd04-002 /
promoy17-035 / promoy17-sp4d02 の3件で、いずれも
rejects に独自行は無く、identity 実測で canon_id は
対象自身（alias 側の canon も dmbd07-a-006）、
aliases_for = 3件。第424弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも対象 id・
alias とも登録なし。登録ブロッカーの確認（第375弾の
教訓）: rule_convert.split（対象行）は None を返し
定型所有は無い＝ツール側ブロッカーなし。

proto T1200（dmbd07-a-006 型、ツインパクト）。
判別役は既存 proto を流用: T1175（ゼロ・ジョーカーズ
役＝マナ役・墓地のジョーカーズ役）/ T1091（通常
クリーチャー役・対照役）/ T1090（スピードアタッカー
役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の
作法）。ゼロ文明の支払いはゼロ文明のマナを要する
（第405弾の観測）ため、マナ役は T1175 を使う。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

STATIC = {"kind": "static", "affects": "self",
          "if": {"exists": {"ref": "self",
                            "filter": {"entered_this_turn": True}}},
          "mod": {"player_rush": True}}
CREATURE_ABILITIES = [STATIC]
SPELL = [{"op": "move",
          "select": {"zone": "graveyard", "owner": "you",
                     "filter": {"race_has": "ジョーカーズ"}, "count": 1},
          "to": "mana", "reason": "put"}]
CREATURE_TEXT = ("W・ブレイカー（このクリーチャーはシールドを"
                 "２つブレイクする）\n"
                 "このクリーチャーは、バトルゾーンに出たターンの間、"
                 "相手プレイヤーを攻撃できる。")
SPELL_TEXT = "ジョーカーズを１枚、自分の墓地からマナゾーンに置く。"
FULL_TEXT = CREATURE_TEXT + " ／ " + SPELL_TEXT
NAME = "ガンバＧ/ガガン・ガン・ガガン"


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _raw_form():
    return {"id": "T1200", "name": NAME, "mana": 1, "text": FULL_TEXT,
            "faces": [
                {"name": "ガンバＧ", "types": ["creature"],
                 "civs": ["zero"], "cost": 6, "power": 6000,
                 "races": ["ジョーカーズ"], "text": CREATURE_TEXT,
                 "keywords": ["double_breaker"],
                 "abilities": copy.deepcopy(CREATURE_ABILITIES)},
                {"name": "ガガン・ガン・ガガン", "types": ["spell"],
                 "civs": ["zero"], "cost": 2, "text": SPELL_TEXT,
                 "spell": copy.deepcopy(SPELL)}]}


def test_proto_form(rules):
    c = proto_card("T1200")
    assert c["name"] == NAME and c["mana"] == 1
    assert c["text"] == FULL_TEXT
    f0, f1 = c["faces"]
    assert f0["name"] == "ガンバＧ"
    assert f0["types"] == ["creature"] and f0["civs"] == ["zero"]
    assert f0["cost"] == 6 and f0["power"] == 6000
    assert f0["races"] == ["ジョーカーズ"]
    assert f0["text"] == CREATURE_TEXT
    assert f0["keywords"] == ["double_breaker"]
    assert f0["abilities"] == CREATURE_ABILITIES
    assert f1["name"] == "ガガン・ガン・ガガン"
    assert f1["types"] == ["spell"] and f1["civs"] == ["zero"]
    assert f1["cost"] == 2 and f1["text"] == SPELL_TEXT
    assert f1["spell"] == SPELL
    d = parse_card(copy.deepcopy(c), TABLES)
    pf0, pf1 = d.faces
    assert STATIC in pf0.abilities
    # double_breaker はキーワード展開で static が1件増える
    assert len(pf0.abilities) == 2
    assert pf0.keywords == ["double_breaker"]
    assert pf1.spell == SPELL
    for tid in ("T1175", "T1091", "T1090"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card(_raw_form(), TABLES)
    pf0, pf1 = d.faces
    assert STATIC in pf0.abilities
    assert len(pf0.abilities) == 2  # キーワード展開分を含む
    assert pf1.spell == SPELL


def _bad(mut):
    c = _raw_form()
    mut(c)
    with pytest.raises(DefError):
        parse_card(c, TABLES)


def test_bad_player_rush_not_true():
    _bad(lambda c: c["faces"][0]["abilities"][0].update(
        mod={"player_rush": False}))


def test_bad_unknown_mod_key():
    _bad(lambda c: c["faces"][0]["abilities"][0].update(
        mod={"bogus_mod": True}))


def test_bad_exists_filter_key():
    _bad(lambda c: c["faces"][0]["abilities"][0].update(
        **{"if": {"exists": {"ref": "self",
                             "filter": {"bogus_key": True}}}}))


def test_bad_spell_unknown_op():
    _bad(lambda c: c["faces"][1].update(spell=[{"op": "bogus_op"}]))


def test_bad_spell_unknown_zone():
    _bad(lambda c: c["faces"][1].update(spell=[
        {"op": "move",
         "select": {"zone": "sideways", "owner": "you", "count": 1},
         "to": "mana", "reason": "put"}]))


def _build(rules, p0, p1, filler="T002"):
    return scenario.build(rules, {"p0": p0, "p1": p1, "filler": filler,
                                  "seed": 1, "deck_size": 20})


def _in_zone(e, p, zone, defn):
    return [c for c in e.zlist(zone, p) if e.s.cards[c].defn == defn]


def _cid(e, defn, p):
    return next(c for c in e.bz_tops(p) if e.cdef(c).id == defn)


def _step_default(e, d):
    keys = [o["key"] for o in d["options"]]
    if d["kind"] == "pay_mana":
        e.answer(list(range(d["min"])))
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    elif "no_block" in keys:
        e.answer([keys.index("no_block")])
    elif d["kind"] == "declare_strigger":
        e.answer([])
    else:
        e.answer(list(range(d.get("min", 0))))


def test_chars_player_rush_only_on_entry_turn(rules):
    """特性レベルの判別: 出たターンだけ player_rush が
    付き、攻撃選択肢はプレイヤーへの攻撃のみ（タップ
    している相手クリーチャーがいてもクリーチャーへの
    攻撃は提示されない＝召喚酔いはバイパスしない）。
    前ターンからいれば player_rush は付かず、
    クリーチャーへの攻撃が提示される。"""
    e = _build(rules, {"bz": ["T1200"]}, {"bz": ["T1091"]})
    src = _cid(e, "T1200", 0)
    opp = _cid(e, "T1091", 1)
    e.s.mut_card(opp).tapped = True
    e.s.mut_card(src).entered_turn = e.s.turn
    assert e.chars(src)["player_rush"] is True
    keys = [o["key"] for o in e._attack_options(0)]
    assert "attack:T1200:player" in keys
    assert not [k for k in keys if k.startswith("attack:T1200:T")]
    e.s.mut_card(src).entered_turn = e.s.turn - 1
    assert e.chars(src)["player_rush"] is False
    keys = [o["key"] for o in e._attack_options(0)]
    assert "attack:T1200:T1091" in keys


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
        _step_default(e, d)
    return seen


def test_summon_and_break_two_shields_same_turn(rules):
    """実挙動: 召喚したターンに相手プレイヤーを攻撃
    でき、W・ブレイカーでシールドが2枚減る。"""
    e = _build(rules,
               {"hand": ["T1200"],
                "mana": ["T1175", "T1175", "T1175",
                         "T1175", "T1175", "T1175"]},
               {})
    before = len(e.zlist("shield", 1))
    seen = _drive(e, player=0, play="T1200:0", attack="T1200")
    assert seen["played"] and seen["attacked"]
    assert len(e.zlist("shield", 1)) == before - 2


def test_control_vanilla_cannot_attack_on_entry_turn(rules):
    """対照: 通常クリーチャーは出たターンに攻撃
    できない（player_rush の判別）。"""
    e = _build(rules,
               {"hand": ["T1091"], "mana": ["T1091", "T1091"]},
               {"bz": ["T1091"]})
    seen = _drive(e, player=0, play="T1091", attack="T1091")
    assert seen["played"]
    assert not seen["attacked"]
    assert not [k for k in seen["attack_keys"]
                if k.startswith("attack:T1091:")]


def _cast_spell_face(e, done, limit=600):
    cast = False
    for _ in range(limit):
        if cast and done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not cast and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T1200:1" in keys:
            cast = True
            e.answer([keys.index("play:T1200:1")])
            continue
        _step_default(e, d)
    return done()


def test_spell_face_moves_jokers_from_graveyard_to_mana(rules):
    """呪文面の実挙動: 墓地のジョーカーズ（T1175）が
    1枚マナゾーンに置かれ、ジョーカーズでない
    カード（T1091）は墓地に残る。"""
    e = _build(rules,
               {"hand": ["T1200"], "mana": ["T1175", "T1175"],
                "graveyard": ["T1175", "T1091"]},
               {})
    ok = _cast_spell_face(
        e, lambda: len(_in_zone(e, 0, "mana", "T1175")) == 3)
    assert ok
    assert not _in_zone(e, 0, "graveyard", "T1175")
    assert _in_zone(e, 0, "graveyard", "T1091")


def test_spell_face_without_jokers_moves_nothing(rules):
    """呪文面の判別: 墓地にジョーカーズが無ければ
    何も置かれず、呪文は通常どおり墓地に置かれる。"""
    e = _build(rules,
               {"hand": ["T1200"], "mana": ["T1175", "T1175"],
                "graveyard": ["T1091"]},
               {})
    ok = _cast_spell_face(
        e, lambda: bool(_in_zone(e, 0, "graveyard", "T1200")))
    assert ok
    assert len(_in_zone(e, 0, "mana", "T1175")) == 2
    assert _in_zone(e, 0, "graveyard", "T1091")
