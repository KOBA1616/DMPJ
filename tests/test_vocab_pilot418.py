"""語彙パイロット第418弾: all_civilizations_mana（ドリフト）。

センサス（rejects 1,914件を取り直し）: pure 1,766件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜417弾）は原則として再提案しない。
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

範囲内・最小の **all_civilizations_mana（pure 1件、
multi にも現れない）** を選定した。本候補は第376弾で
「ツインパクトで第3条項〔手札からマナに置いた時
アンタップ〕が未組立て」として見送られたが、本弾で
第3条項の確立形を確認したため再評価した（第410・
411弾と同じ型の覆し）:
- 第3条項は登録済み dm24bd5-033 配信妖精コスメの
  監視誘発（trigger {when: {event: move, to: mana,
  subject: {owner: you, filter: {multicolor: true}},
  first_time: true} → untap {select: {ref:
  event.subject}}）から first_time と multicolor
  フィルタを外し、文面どおり from: hand を足した形。
  when の from は defs 検証・schema.py の when
  定義・エンジン _match_when のいずれでも受理される
  ことを確認した。
- 第1条項（出た時、山札の上から1枚をマナゾーンに
  置く）は move {select: {zone: deck, owner: you,
  from_top: 1}, to: mana, reason: put}（第376弾・
  登録済み dmex14-083 等の形）。
- 第2条項（自分のマナゾーンにあるカードは、すべての
  文明を持つ）は第376弾の確立形 static {affects:
  {zone: mana, owner: you}, mod: {add_civs:
  [light, water, darkness, fire, nature]}}（登録済み
  dmex01-014 と同文・同形。第260弾の常在キー
  mana_all_civs は支払い計算専用で意味が違うため
  使わない＝第376弾の判断どおり）。
- 呪文面（S・トリガー／コスト5以上のクリーチャーを
  すべて持ち主の手札に戻す）は keywords [s_trigger]
  ＋ spell [bounce {select: {zone: bz, owner: any,
  filter: {types: [creature], cost_ge: 5},
  count: all}}]（bounce の count: all は登録済み
  dm25ex2-035 等、owner: any の bounce は
  converted に70件）。

対象は dm26sd1-u010 怪盗妖精カサブランカ /
「信じていたのに裏切られるなんて！」（ツインパクト。
クリーチャー面: 自然 / コスト3 / パワー2000 /
種族 スノーフェアリー。呪文面: 水 / コスト6）。
partial は骨格のみ（types [creature] のみで
faces 無し、text は第2条項の断片、abilities 無し）。
**補完あり: faces 構造＋text**（両面とも公式全文。
最上位 text は両面を「 ／ 」で連結）。alias は
dm24bd5-010 / dm25ex3-tf27 / dm25rp4-t09 の3件で
rejects に独自行は無く、identity 実測で canon_id は
対象自身（alias 側の canon も dm26sd1-u010）、
aliases_for = 3件。第418弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも対象 id・
alias とも登録なし。登録ブロッカーの確認
（第375弾の教訓）: rule_convert.split（対象行）は
None を返し定型所有は無い＝ツール側ブロッカーなし。

proto T1189（dm26sd1-u010 型、ツインパクト）。
判別役は既存 proto を流用: T001（自然バニラ・
マナ役）/ T002（フィラー）/ T030（光水の多色＝
タップ入り判別役）/ T277（火・コスト2＝支払い
判別役）/ T1139（コスト5・パワー6000役）/
T008（コスト2・闇役）。

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

CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "effect": [{"op": "move",
                   "select": {"zone": "deck", "owner": "you", "from_top": 1},
                   "to": "mana", "reason": "put"}]}
STATIC = {"kind": "static",
          "affects": {"zone": "mana", "owner": "you"},
          "mod": {"add_civs": ["light", "water", "darkness",
                               "fire", "nature"]}}
WATCH = {"kind": "trigger",
         "when": {"event": "move", "from": "hand", "to": "mana",
                  "subject": {"owner": "you"}},
         "effect": [{"op": "untap", "select": {"ref": "event.subject"}}]}
CREATURE_ABILITIES = [CIP, STATIC, WATCH]
SPELL = [{"op": "bounce",
          "select": {"zone": "bz", "owner": "any",
                     "filter": {"types": ["creature"], "cost_ge": 5},
                     "count": "all"}}]
# parse 後: bounce は move（to: hand, reason: return）に正規化される
PARSED_SPELL = [{"op": "move",
                 "select": {"zone": "bz", "owner": "any",
                            "filter": {"types": ["creature"], "cost_ge": 5},
                            "count": "all"},
                 "to": "hand", "reason": "return"}]
CREATURE_TEXT = ("このクリーチャーが出た時、自分の山札の上から１枚を"
                 "マナゾーンに置く。\n"
                 "自分のマナゾーンにあるカードは、すべての文明を持つ。\n"
                 "カードを自分の手札からマナゾーンに置いた時、"
                 "そのカードをアンタップする。")
SPELL_TEXT = ("S・トリガー（このカードを自分のシールドゾーンから"
              "手札に加える時、コストを支払わずにすぐ実行してもよい）\n"
              "コスト５以上のクリーチャーをすべて持ち主の手札に戻す。")
FULL_TEXT = CREATURE_TEXT + " ／ " + SPELL_TEXT
NAME = "怪盗妖精カサブランカ / 「信じていたのに裏切られるなんて！」"


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _raw_form():
    return {"id": "T1189", "name": NAME, "mana": 1, "text": FULL_TEXT,
            "faces": [
                {"name": "怪盗妖精カサブランカ", "types": ["creature"],
                 "civs": ["nature"], "cost": 3, "power": 2000,
                 "races": ["スノーフェアリー"], "text": CREATURE_TEXT,
                 "abilities": copy.deepcopy(CREATURE_ABILITIES)},
                {"name": "「信じていたのに裏切られるなんて！」",
                 "types": ["spell"], "civs": ["water"], "cost": 6,
                 "text": SPELL_TEXT, "keywords": ["s_trigger"],
                 "spell": copy.deepcopy(SPELL)}]}


def test_proto_form(rules):
    c = proto_card("T1189")
    assert c["name"] == NAME and c["mana"] == 1
    assert c["text"] == FULL_TEXT
    f0, f1 = c["faces"]
    assert f0["name"] == "怪盗妖精カサブランカ"
    assert f0["types"] == ["creature"] and f0["civs"] == ["nature"]
    assert f0["cost"] == 3 and f0["power"] == 2000
    assert f0["races"] == ["スノーフェアリー"]
    assert f0["text"] == CREATURE_TEXT
    assert f0["abilities"] == CREATURE_ABILITIES
    assert f1["name"] == "「信じていたのに裏切られるなんて！」"
    assert f1["types"] == ["spell"] and f1["civs"] == ["water"]
    assert f1["cost"] == 6 and f1["text"] == SPELL_TEXT
    assert f1["keywords"] == ["s_trigger"]
    assert f1["spell"] == SPELL
    d = parse_card(copy.deepcopy(c), TABLES)
    pf0, pf1 = d.faces
    for a in CREATURE_ABILITIES:
        assert a in pf0.abilities
    assert len(pf0.abilities) == 3
    assert pf1.spell == PARSED_SPELL
    assert pf1.keywords == ["s_trigger"]
    for tid in ("T001", "T002", "T008", "T030", "T277", "T1139"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card(_raw_form(), TABLES)
    pf0, pf1 = d.faces
    for a in CREATURE_ABILITIES:
        assert a in pf0.abilities
    assert pf1.spell == PARSED_SPELL


def _bad(mut):
    c = _raw_form()
    mut(c)
    with pytest.raises(DefError):
        parse_card(c, TABLES)


def test_bad_add_civs_unknown_civ():
    _bad(lambda c: c["faces"][0]["abilities"][1].update(
        mod={"add_civs": ["light", "bogus"]}))


def test_bad_add_civs_empty():
    _bad(lambda c: c["faces"][0]["abilities"][1].update(
        mod={"add_civs": []}))


def test_bad_watch_from_zone():
    _bad(lambda c: c["faces"][0]["abilities"][2].update(
        when={"event": "move", "from": "sideways", "to": "mana",
              "subject": {"owner": "you"}}))


def test_bad_spell_filter_key():
    _bad(lambda c: c["faces"][1].update(spell=[
        {"op": "bounce",
         "select": {"zone": "bz", "owner": "any",
                    "filter": {"types": ["creature"], "bogus_key": 1},
                    "count": "all"}}]))


def test_bad_spell_unknown_op():
    _bad(lambda c: c["faces"][1].update(spell=[{"op": "bogus_op"}]))


def _build(rules, p0, p1, filler="T002"):
    return scenario.build(rules, {"p0": p0, "p1": p1, "filler": filler,
                                  "seed": 1, "deck_size": 20})


def _in_zone(e, p, zone, defn):
    return [c for c in e.zlist(zone, p) if e.s.cards[c].defn == defn]


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


def _play_creature_face(e, done, limit=600):
    played = False
    for _ in range(limit):
        if played and done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T1189:0" in keys:
            played = True
            e.answer([keys.index("play:T1189:0")])
            continue
        _step_default(e, d)
    return done()


def test_cip_puts_deck_top_to_mana(rules):
    """第1条項の実挙動: 出た時、山札の上から1枚が
    マナゾーンに置かれる（マナ+1・山札-1）。"""
    e = _build(rules, {"hand": ["T1189"], "mana": ["T001", "T001", "T001"]},
               {})
    deck0, mana0 = len(e.zlist("deck", 0)), len(e.zlist("mana", 0))
    ok = _play_creature_face(e, lambda: bool(_in_zone(e, 0, "bz", "T1189")))
    assert ok
    assert len(e.zlist("mana", 0)) == mana0 + 1
    assert len(e.zlist("deck", 0)) == deck0 - 1


def test_cip_move_does_not_trigger_clause3(rules):
    """from: hand の判別: 第1条項で山札からマナに
    置かれた多色カード（フィラー T030）は 405.1 で
    タップして置かれ、第3条項ではアンタップされない
    （手札からではないため）。"""
    e = _build(rules, {"hand": ["T1189"], "mana": ["T001", "T001", "T001"]},
               {}, filler="T030")
    ok = _play_creature_face(e, lambda: bool(_in_zone(e, 0, "bz", "T1189")))
    assert ok
    moved = _in_zone(e, 0, "mana", "T030")
    assert len(moved) == 1
    assert e.s.cards[moved[0]].tapped is True


def test_mana_all_civs_chars(rules):
    """第2条項の特性判別: 発生源がいれば自分のマナの
    自然カードはすべての文明を持ち、いなければ
    自然のみ。"""
    e = _build(rules, {"bz": ["T1189"], "mana": ["T001"]}, {})
    cid = _in_zone(e, 0, "mana", "T001")[0]
    assert sorted(e.chars(cid)["civs"]) == [
        "darkness", "fire", "light", "nature", "water"]
    e2 = _build(rules, {"mana": ["T001"]}, {})
    cid2 = _in_zone(e2, 0, "mana", "T001")[0]
    assert sorted(e2.chars(cid2)["civs"]) == ["nature"]


def _main_keys(e, player):
    for _ in range(300):
        d = e.advance()
        if d is None:
            return None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == player:
            return keys
        _step_default(e, d)
    return None


def test_pay_fire_cost_with_nature_mana(rules):
    """第2条項の支払い判別: 発生源がいれば自然マナ
    だけで火コスト（T277）を支払える。対照では
    支払えない。"""
    e = _build(rules, {"bz": ["T1189"], "hand": ["T277"],
                       "mana": ["T001", "T001"]}, {})
    assert "play:T277" in _main_keys(e, 0)
    e2 = _build(rules, {"hand": ["T277"], "mana": ["T001", "T001"]}, {})
    assert "play:T277" not in _main_keys(e2, 0)


def _charge_and_read(e, player, tid):
    """player の最初の charge で tid を置き、同ターン内に
    収まる範囲で誘発解決まで進めてから tapped を読む
    （第417弾の作法＋ターン境界で打ち切り）。"""
    for _ in range(300):
        d = e.advance()
        if d is None:
            return None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge" and d.get("player") == player:
            hit = [i for i, k in enumerate(keys) if tid in k]
            if not hit:
                _step_default(e, d)
                return None
            turn = e.s.turn
            e.answer([hit[0]])
            for _ in range(40):
                if e.s.turn != turn:
                    break
                d2 = e.advance()
                if d2 is None:
                    break
                _step_default(e, d2)
                if e.s.turn != turn:
                    break
            m = _in_zone(e, player, "mana", tid)
            return e.s.cards[m[0]].tapped if m else None
        _step_default(e, d)
    return None


def test_charge_multicolor_untapped_by_clause3(rules):
    """第3条項の実挙動: 発生源がいれば、手札から
    マナに置いた多色カード（T030、405.1 でタップ
    して置かれる）は誘発でアンタップされる。"""
    e = _build(rules, {"bz": ["T1189"], "hand": ["T030"]}, {})
    assert _charge_and_read(e, 0, "T030") is False


def test_charge_multicolor_control_stays_tapped(rules):
    """対照: 発生源がなければ、多色カードはタップ
    したまま置かれる。"""
    e = _build(rules, {"hand": ["T030"]}, {})
    assert _charge_and_read(e, 0, "T030") is True


def test_opponent_charge_not_untapped(rules):
    """subject {owner: you} の判別: 相手が手札から
    マナに置いた多色カードはアンタップされない。"""
    e = _build(rules, {"bz": ["T1189"]}, {"hand": ["T030"]})
    assert _charge_and_read(e, 1, "T030") is True


def test_spell_face_bounces_all_cost_ge_5(rules):
    """呪文面の実挙動: コスト5以上のクリーチャーは
    両プレイヤーともすべて持ち主の手札に戻り、
    コスト2は残る。"""
    e = _build(rules,
               {"hand": ["T1189"],
                "mana": ["T030", "T001", "T001", "T001", "T001", "T001"],
                "bz": ["T1139", "T001"]},
               {"bz": ["T1139", "T008"]})
    cast = False
    for _ in range(600):
        if cast and not _in_zone(e, 0, "bz", "T1139"):
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not cast and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T1189:1" in keys:
            cast = True
            e.answer([keys.index("play:T1189:1")])
            continue
        _step_default(e, d)
    assert cast
    assert not _in_zone(e, 0, "bz", "T1139")
    assert _in_zone(e, 0, "hand", "T1139")
    assert _in_zone(e, 0, "bz", "T001")          # コスト2は残る
    assert not _in_zone(e, 1, "bz", "T1139")
    assert _in_zone(e, 1, "hand", "T1139")
    assert _in_zone(e, 1, "bz", "T008")          # 相手のコスト2も残る
