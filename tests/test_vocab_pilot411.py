"""語彙パイロット第411弾: madness（ドリフト）。

センサス（rejects 1,921件を取り直し）: pure 1,773件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜410弾）は原則として再提案しない。
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
first_time_tap（pure 2、第410弾で記録）は新規語彙
候補として残置のまま。

**madness の過去の却下と、それを覆す新根拠**:
madness（pure 2件）は第379弾で「手札破壊の置換照合が
要り CIP の複合効果も残る」、第385弾・第394弾でも
同根として却下されてきた。しかし第409弾が、同一
文面系統のマッドネス条項（dm26ex3-010 の第3条項）を
登録済み dm26ex3-dcr005 の登録形と完全一致する
replace 形で実挙動検証した（相手呪文で捨てられれば
置換で出る／任意で断れる／自分の呪文では by: opp
判別で発火しない）。「置換照合が未実装」という
却下の前提は崩れており、第410弾が force_block の
却下を覆したのと同じ型の覆しとして再評価する。
範囲内・最小の **madness のうち dmx18-047 の1件**
を選定した（第400弾の untap_restriction と同じ
扱い: ファミリーは解消しない）。

対象は dmx18-047 有毒類罠顎目 ドクゲーター
（自然のクリーチャー / コスト5 / パワー4000 /
種族 ジュラシック・コマンド・ドラゴン）。partial は
骨格完備（mana 1、keywords・abilities ともに無し）で、
未解決は source.unsupported の madness 1件だけ。
partial の text は断片（「捨てられる時」）のため
**補完あり: text のみ**。alias は無い（identity
実測で canon_id は対象自身、aliases_for = []）。
第411弾時点で real.yaml / real_akashic.yaml /
real_vocab.yaml / real_zone.yaml / proto.yaml /
converted.yaml のいずれにも登録なし。単面カードで
未検証の面は無い。登録ブロッカーの確認（第375弾の
教訓）: rule_convert.split（対象行）は None を返し
定型所有は無い（本弾で実測）。

ファミリーの残り1件 dmx26-028 熱血提督
ザーク・タイザーは対象外: 第2条項（山札の上から
3枚を表向きにし、ヒューマノイド爆とコマンド・
ドラゴンをすべて手札に加え、残りを好きな順序で
山札の一番下に置く）が公開＋種族抜き＋順序付け
戻しの複合で、look/reorder 系の未確立機構が要る。

結論はドリフト（追加語彙なし）。確立形は
abilities 2件（文面の条項順）:
- 第1条項（マッドネス）は replace {zone: hand,
  optional: true, when: {event: move, from: hand,
  to: graveyard, reason: discard, subject: self,
  by: opp}, instead: [{op: move, select:
  {ref: self, count: 1}, to: bz, reason: put}]}。
  登録済み dm26ex3-dcr005 の登録形と完全一致
  （by: opp は第40弾で確立。zone: hand 宣言の
  置換のため第386弾の発生源走査制限は及ばない）。
- 第2条項（出た時）は trigger {when: {event: move,
  to: bz, subject: self}, effect: [choose
  {select: {zone: bz, owner: opp, filter:
  {cost_le: 4}, count: 1}, as: pick}, mana_put
  {select: {ref: pick}}]}。第389弾・登録済み
  dmex10-014 の CIP 形のフィルタを {types:
  [creature]} から {cost_le: 4} に替えたもの。
  文面は「クリーチャー」ではなく「カード」のため
  types フィルタは付けない（タマシードも対象）。
  cost_le は FILTER_KEYS の既存キーで登録先例
  dm23rp1-074 があり、defs と schema.py の両側に
  定義済み（第408ラウンドの教訓）。

proto T1179（dmx18-047 型）。判別役は既存 proto を
流用: T001（コスト2クリーチャー役・自然マナ役）/
T004（コスト3ブロッカー役）/ T116（コスト6役＝
候補外の判別）/ T117（相手の手札を捨てさせる
呪文役）/ T118（自分の手札を捨てる呪文役）/
T189（コスト3タマシード役＝「カード」判別）/
T008（闇マナ役）。

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

MADNESS = {"kind": "replace", "zone": "hand", "optional": True,
           "when": {"event": "move", "from": "hand",
                    "to": "graveyard", "reason": "discard",
                    "subject": "self", "by": "opp"},
           "instead": [{"op": "move",
                        "select": {"ref": "self", "count": 1},
                        "to": "bz", "reason": "put"}]}
CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "effect": [{"op": "choose",
                   "select": {"zone": "bz", "owner": "opp",
                              "filter": {"cost_le": 4},
                              "count": 1},
                   "as": "pick"},
                  {"op": "mana_put", "select": {"ref": "pick"}}]}
FORM = [MADNESS, CIP]
# parse_card はマクロを展開するため、検証後の CIP は
# mana_put → move {to: mana, reason: put} の展開形になる
# （第389弾で実測。本弾でも実測）
EXPANDED = [MADNESS,
            {"kind": "trigger",
             "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [CIP["effect"][0],
                        {"op": "move", "select": {"ref": "pick"},
                         "to": "mana", "reason": "put"}]}]
FULL_TEXT = ("相手の呪文の効果またはクリーチャーの能力によって、"
             "このクリーチャーが自分の手札から捨てられる時、"
             "墓地に置くかわりにバトルゾーンに出してもよい。\n"
             "このクリーチャーをバトルゾーンに出した時、"
             "バトルゾーンにある相手のコスト４以下のカードを"
             "１枚選び、持ち主のマナゾーンに置く。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1179")
    assert c["abilities"] == FORM
    assert c["name"] == "有毒類罠顎目 ドクゲーター"
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 5 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ジュラシック・コマンド・ドラゴン"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.abilities == EXPANDED
    for tid in ("T001", "T004", "T008", "T116", "T117", "T118",
                "T189"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX411", "name": "有毒類罠顎目 ドクゲーター",
                    "types": ["creature"], "civs": ["nature"],
                    "cost": 5, "power": 4000, "mana": 1,
                    "races": ["ジュラシック・コマンド・ドラゴン"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert d.abilities == EXPANDED


def _bad(ability):
    with pytest.raises(DefError):
        parse_card({"id": "TX411B", "name": "x", "types": ["creature"],
                    "civs": ["nature"], "cost": 5, "power": 4000,
                    "abilities": [ability]}, TABLES)


def test_bad_by_value():
    _bad({"kind": "replace", "zone": "hand", "optional": True,
          "when": {"event": "move", "from": "hand",
                   "to": "graveyard", "reason": "discard",
                   "subject": "self", "by": "bogus"},
          "instead": [{"op": "move",
                       "select": {"ref": "self", "count": 1},
                       "to": "bz", "reason": "put"}]})


def test_bad_unknown_filter_key():
    bad = copy.deepcopy(CIP)
    bad["effect"][0]["select"]["filter"]["bogus_key"] = 1
    _bad(bad)


def test_bad_unknown_op():
    bad = copy.deepcopy(CIP)
    bad["effect"][1] = {"op": "mana_putx", "select": {"ref": "pick"}}
    _bad(bad)


def test_bad_unknown_select_key():
    bad = copy.deepcopy(CIP)
    bad["effect"][0]["select"]["bogus"] = 1
    _bad(bad)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _zone_card(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p)
                if e.s.cards[c].defn == defn)


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
    """第409弾と同型の駆動: player 0 が caster を唱え、
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
    """第1条項の実挙動: 相手の呪文（T117）で捨てられる時、
    置換を選べば墓地ではなくバトルゾーンに出る
    （by: opp、第409弾と同型）。"""
    e = _build(rules, {"hand": ["T117"], "mana": ["T008"] * 4},
               {"hand": ["T1179"]})
    v = _zone_card(e, "hand", 1, "T1179")
    assert _settle(e, lambda: e.s.cards[v].zone == "bz",
                   _discard_drive("T117", "T1179", True))
    assert v in e.zlist("bz", 1)
    assert v not in e.zlist("graveyard", 1)


def test_madness_replace_is_optional(rules):
    """第1条項は任意: 置換を断れば墓地に置かれる。"""
    e = _build(rules, {"hand": ["T117"], "mana": ["T008"] * 4},
               {"hand": ["T1179"]})
    v = _zone_card(e, "hand", 1, "T1179")
    assert _settle(e, lambda: e.s.cards[v].zone == "graveyard",
                   _discard_drive("T117", "T1179", False))
    assert v not in e.zlist("bz", 1)


def test_madness_not_triggered_by_own_spell(rules):
    """by: opp の判別: 自分の呪文（T118）で自分の手札から
    捨てる時は置換が発火せず、墓地に行く。"""
    e = _build(rules,
               {"hand": ["T118", "T1179"], "mana": ["T008"] * 2},
               {})
    v = _zone_card(e, "hand", 0, "T1179")
    assert _settle(e, lambda: e.s.cards[v].zone == "graveyard",
                   _discard_drive("T118", "T1179", True))
    assert v not in e.zlist("bz", 0)


def _boring(d):
    keys = [o["key"] for o in d["options"]]
    for want in ("pass", "end_turn", "end_attack", "end_phase"):
        if want in keys:
            return [keys.index(want)]
    return [0]


def _summon(rules, p1, choose_defn=None):
    """p0 が T1179 を召喚し、CIP の choose に答えて解決まで
    進める（第389弾と同型）。（engine, 召喚したか,
    choose 判断が出たか）を返す。"""
    e = _build(rules, {"hand": ["T1179"], "mana": ["T001"] * 5}, p1)
    played = False
    chose = False
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T1179" in keys:
            played = True
            e.answer([keys.index("play:T1179")])
            continue
        if played and d["kind"] == "choose_cards":
            chose = True
            idx = [i for i, o in enumerate(d["options"])
                   if choose_defn in o["key"]]
            assert idx, f"{choose_defn} が選択肢に無い: {keys}"
            e.answer(idx[:1])
            continue
        if played and d["kind"] in ("main", "charge", "attack"):
            break          # 解決が終わり次の通常判断に戻った
        e.answer(_boring(d))
    return e, played, chose


def _mana_defns(e, p):
    return [e.cdef(c).id for c in e.zlist("mana", p)]


def _bz_defns(e, p):
    """バトルゾーンは共有ゾーンのため controller で絞る
    （第389弾の作法）。"""
    return [e.cdef(c).id for c in e.zlist("bz", p)
            if e.s.cards[c].controller == p]


def test_cip_cost2_creature_to_owner_mana(rules):
    """第2条項の実挙動: 相手のコスト2クリーチャー（T001）を
    選ぶと、持ち主（相手）のマナゾーンに置かれる。"""
    e, played, chose = _summon(rules, {"bz": ["T001"]}, "T001")
    assert played
    assert chose is False           # 候補1枚では選択判断が出ず自動で決まる
    assert _mana_defns(e, 1) == ["T001"]
    assert _bz_defns(e, 1) == []
    assert "T1179" in _bz_defns(e, 0)


def test_cip_choose_cost3_among_two(rules):
    """候補が2枚（コスト2とコスト3）あれば選択が出て、
    コスト3（T004）を選ぶとそちらだけがマナゾーンに
    置かれ、コスト2はバトルゾーンに留まる。"""
    e, played, chose = _summon(rules, {"bz": ["T001", "T004"]}, "T004")
    assert played and chose
    assert _mana_defns(e, 1) == ["T004"]
    assert _bz_defns(e, 1) == ["T001"]


def test_cip_cost6_is_not_a_candidate(rules):
    """cost_le: 4 の判別: 相手のコスト6（T116）は候補に
    ならず、バトルゾーンに留まりマナゾーンにも行かない。"""
    e, played, chose = _summon(rules, {"bz": ["T116"]})
    assert played
    assert chose is False
    assert _mana_defns(e, 1) == []
    assert _bz_defns(e, 1) == ["T116"]


def test_cip_tamaseed_is_a_candidate(rules):
    """「カード」の判別（types フィルタ無し）: 相手の
    タマシード（T189、コスト3）も対象になり、持ち主の
    マナゾーンに置かれる。第389弾の {types: [creature]}
    形との差。"""
    e, played, chose = _summon(rules, {"bz": ["T189"]}, "T189")
    assert played
    assert _mana_defns(e, 1) == ["T189"]
    assert _bz_defns(e, 1) == []


def test_cip_own_creature_is_not_a_candidate(rules):
    """owner: opp の判別: 自分のクリーチャーは候補に
    ならず、自分のバトルゾーンに留まる。"""
    e = _build(rules, {"bz": ["T001"], "hand": ["T1179"],
                       "mana": ["T001"] * 5}, {})
    played = False
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" \
                and d.get("player") == 0 and "play:T1179" in keys:
            played = True
            e.answer([keys.index("play:T1179")])
            continue
        if played and d["kind"] in ("main", "charge", "attack"):
            break
        e.answer(_boring(d))
    assert played
    assert "T001" in _bz_defns(e, 0)
    assert _mana_defns(e, 1) == []


def test_cip_fires_when_entering_via_madness(rules):
    """複合判別: マッドネス置換でバトルゾーンに出た時も
    第2条項は発火する。相手（p0）のコスト2（T001）が
    持ち主（p0）のマナゾーンに置かれる。"""
    e = _build(rules, {"bz": ["T001"], "hand": ["T117"],
                       "mana": ["T008"] * 4},
               {"hand": ["T1179"]})
    v = _zone_card(e, "hand", 1, "T1179")
    t = _zone_card(e, "bz", 0, "T001")
    assert _settle(e, lambda: e.s.cards[t].zone == "mana",
                   _discard_drive("T117", "T1179", True))
    assert e.s.cards[v].zone == "bz"
    assert t in e.zlist("mana", 0)
    assert t not in e.zlist("bz", 0)
