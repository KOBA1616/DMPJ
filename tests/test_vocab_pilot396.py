"""語彙パイロット第396弾: power_per_civilization（ドリフト）。

センサス（rejects 1,937件を取り直し）: pure 1,789件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜395弾）は再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021 と
battle_opponent_reference の残り1件 dmr01-049 は
先行弾の評価を覆す根拠が無く再提案しない。本弾で
個別に評価して見送った候補: destroyed_this_turn_
condition（pure 1、dm26ex2-mc012。第392・393・395弾の
次点だが依然として最小ではない: partial も reason も
無い素行の呪文で3条項あり、第1条項は手札ゾーンの
ターン終了時無償詠唱の付与で確立形が未検証のまま。
次点として残す）、distinct_civ_count（pure 1、
dmx19-s45。第395弾で後続候補とされた3条項の複合で
本弾より重い。後続候補のまま残す）、attack_count_
this_turn_condition（pure 1、dm25ex3-014。第388弾の
評価がそのまま成立: 墓地からの自己出場＋超魂X＋
partial の CIP 重複で本 gap 単独では登録形が定まら
ない）、keyword_exists_condition（pure 1、dmr07-010。
第395弾の評価どおりキーワード所持での exists /
フィルタは未検証の別系統が要る）。範囲内・最小の
**power_per_civilization（pure 1件、multi にも
現れない）** を選定した。第395弾で「選んだ（破壊
していない）クリーチャーの文明数を modify の
power amount に {mul} で掛ける位置の検証が追加で
要る」として後続候補に残された候補で、本弾がその
検証を行った。

対象は pure 1件すべて: dm25-055 虹色の霊光
（自然の呪文 / コスト3）。partial は骨格（types
[spell] / civs [nature] / cost 3 / mana 1、
keywords・abilities・spell ともに無し）で、
未解決は unsupported の power_per_civilization
1件だけ。partial の text は条項の断片（「その
クリーチャーが持つ文明ひとつにつき+2000」）の
ため、提出形の text は行の公式テキスト全文を
入れる（**補完あり: text のみ**）。alias は無い
（identity 実測で canon_id(dm25-055) = dm25-055、
aliases_for = []）。第396弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも登録なし。
単面カードで未検証の面は無い。

条項「このターン、バトルゾーンにある自分の
クリーチャー１体のパワーは、そのクリーチャーが
持つ文明ひとつにつき+2000される。カードを
１枚引く。」の確立形は spell の4 op:

- choose {select: {zone: bz, owner: you, filter:
  {types: [creature]}, count: 1}, as: pick}
  （第368・385弾の choose 確立形。所有者は you）
- set_var {name: p_up, value: {mul: [{civ_count:
  {ref: pick}}, 2000]}}（第79弾の式 civ_count を
  第322弾の set_var で数えて束縛する。mul は
  defs の式として検証済み）
- modify {select: {ref: pick}, mod: {power:
  {amount: {var: p_up}}}, duration: end_of_turn}
  （amount の {var:} は op_modify の生成時ベイク
  〈基盤B4〉でリテラルに固定される）
- draw {player: you, count: 1}

当初候補形は2つとも不成立だった（本弾で実測）:
(a) mod power {amount: 2000, count: {civ_count:
{ref: pick}}} は、mod の count が特性計算時に
env_self（{you, self} のみで、解決時の束縛 vars を
含まない）で評価されるため、candidates の ref 分岐が
env["vars"] を引けず {ref: pick} が空に倒れる。
(b) count: {civ_count: {ref: self}} は、civ_count の
評価が chars_ro 経由で同じカードの特性計算へ再入し
RecursionError になる（distinct_cost_count の
_distinct_costing のような再入ガードは civ_count の
経路に無い。本弾の probe で実測）。そこで第395弾の
「移動前に数えて束縛する」確立パターンを、対象が
移動しない本件では「修整の生成前に数えて束縛する」
形で適用した。civ_count / mul / set_var / var は
defs と schema.py（生成済み card.schema.json）の
両側に定義済みを確認（第408ラウンドの教訓）。
候補が無ければ choose は空で p_up は 0、modify は
対象なしで生成されず、ドローだけが解決する
（文面の2文は独立）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（本弾で実測）。

proto T1163（dm25-055 型）。判別役は既存 proto を
流用: T030（光・水の多色クリーチャー＝文明2つ役）/
T1157（火・単色クリーチャー＝文明1つ役・2候補時の
対照役）/ T001（自然クリーチャー＝マナ役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

SPELL = [{"op": "choose",
          "select": {"zone": "bz", "owner": "you",
                     "filter": {"types": ["creature"]},
                     "count": 1},
          "as": "pick"},
         {"op": "set_var", "name": "p_up",
          "value": {"mul": [{"civ_count": {"ref": "pick"}}, 2000]}},
         {"op": "modify", "select": {"ref": "pick"},
          "mod": {"power": {"amount": {"var": "p_up"}}},
          "duration": "end_of_turn"},
         {"op": "draw", "player": "you", "count": 1}]
FORM = SPELL
# parse_card はマクロを展開するが、本形の4 op はすべて
# 素の op（choose / set_var / modify / draw）なので
# 検証後の spell は提出形と同一になる（本弾で実測）
EXPANDED = SPELL
FULL_TEXT = ("このターン、バトルゾーンにある自分のクリーチャー"
             "１体のパワーは、そのクリーチャーが持つ文明ひとつに"
             "つき+2000される。\nカードを１枚引く。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1163")
    assert c["name"] == "虹色の霊光"
    assert c["types"] == ["spell"]
    assert c["civs"] == ["nature"]
    assert c["cost"] == 3 and c["mana"] == 1
    assert not c.get("keywords")
    assert not c.get("abilities")
    assert c["text"] == FULL_TEXT
    assert c["spell"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.spell == EXPANDED          # マクロ展開後の形（＝提出形）
    for tid in ("T030", "T1157", "T001"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX396", "name": "x",
                    "types": ["spell"], "civs": ["nature"],
                    "cost": 3, "mana": 1,
                    "spell": copy.deepcopy(FORM)}, TABLES)
    assert d.spell == EXPANDED


def test_bad_forms_rejected(rules):
    # mod power の amount への {mul} は DefError
    # （amount は int / {var:} / {power_of:} のみ。第395弾の
    # 未検証点だった「amount に {mul} で掛ける位置」は
    # defs の検証自体が受理しない）
    bad = copy.deepcopy(proto_card("T1163"))
    bad["spell"][2]["mod"] = {"power": {"amount": {"mul": [{"var": "p_up"}, 1]}}}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # 未知の op 名は DefError
    bad2 = copy.deepcopy(proto_card("T1163"))
    bad2["spell"][0] = {"op": "choosex",
                        "select": {"zone": "bz", "owner": "you", "count": 1},
                        "as": "pick"}
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)
    # 未知の mod キーは DefError
    bad3 = copy.deepcopy(proto_card("T1163"))
    bad3["spell"][2]["mod"] = {"powerx": 2000}
    with pytest.raises(DefError):
        parse_card(bad3, TABLES)


def _build(rules, p0, p1=None):
    return scenario.build(rules, {"p0": p0, "p1": p1 or {},
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _count(e, zone, p):
    if zone == "bz":
        return len(e.bz_tops(p))
    return len(e.zlist(zone, p))


def _power(e, defn, p=0):
    for c in e.bz_tops(p):
        if e.cdef(c).id == defn:
            return e.chars(c)["power"]
    raise AssertionError(f"{defn} がバトルゾーンに無い")


def _boring(d):
    keys = [o["key"] for o in d["options"]]
    for want in ("pass", "end_turn", "end_attack", "end_phase"):
        if want in keys:
            return [keys.index(want)]
    return [0]


def _cast(rules, p0, p1=None, choose_defn=None):
    """p0 が T1163 を唱え、choose が出れば choose_defn を
    選んで解決まで進める。（engine, 唱えたか, choose
    判断が出たか, 詠唱直前の手札枚数）を返す。"""
    e = _build(rules, p0, p1)
    cast = False
    chose = False
    hand0 = None
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not cast and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T1163" in keys:
            cast = True
            hand0 = _count(e, "hand", 0)
            e.answer([keys.index("play:T1163")])
            continue
        if cast and d["kind"] == "choose_cards":
            chose = True
            if choose_defn is not None:
                idx = [i for i, o in enumerate(d["options"])
                       if choose_defn in o["key"]]
                assert idx, f"{choose_defn} が選択肢に無い: {keys}"
                e.answer(idx[:1])
                continue
            e.answer([0])
            continue
        if cast and d["kind"] in ("main", "charge", "attack"):
            break          # 解決が終わり次の通常判断に戻った
        e.answer(_boring(d))
    return e, cast, chose, hand0


def test_cast_multicolor_gets_plus_4000_and_draws(rules):
    """実挙動: 多色クリーチャー（光・水＝文明2つ）の
    T030（パワー2000）を選ぶと、このターンのパワーは
    2000＋2×2000＝6000 になる（解決前に set_var で
    数えた civ_count {ref: pick} が 2 になることの
    検証）。カードも1枚引く（手札は呪文の消費と
    相殺されて詠唱直前と同数）。候補が1体だけの時は
    choose 判断が出ず自動で選ばれる（本弾で実測）。"""
    e, cast, chose, hand0 = _cast(
        rules,
        {"hand": ["T1163"], "mana": ["T001"] * 3, "bz": ["T030"]},
        choose_defn="T030")
    assert cast and not chose   # 候補1体では自動選択
    assert _power(e, "T030") == 6000
    assert _count(e, "hand", 0) == hand0   # −1（詠唱）＋1（ドロー）
    assert "T1163" in _defns(e, "graveyard", 0)


def test_cast_monocolor_gets_plus_2000(rules):
    """実挙動: 単色クリーチャー（火＝文明1つ）の
    T1157（パワー2000）を選ぶと +2000 の 4000 に
    なる（候補1体では自動選択）。"""
    e, cast, chose, _ = _cast(
        rules,
        {"hand": ["T1163"], "mana": ["T001"] * 3, "bz": ["T1157"]},
        choose_defn="T1157")
    assert cast and not chose   # 候補1体では自動選択
    assert _power(e, "T1157") == 4000


def test_choice_determines_amount(rules):
    """判別: 候補が2体（多色 T030 と単色 T1157）いて
    単色を選ぶと単色だけが +2000 され、多色は元の
    パワーのまま。数は選んだクリーチャーの文明数に
    従う。"""
    e, cast, chose, _ = _cast(
        rules,
        {"hand": ["T1163"], "mana": ["T001"] * 3,
         "bz": ["T030", "T1157"]},
        choose_defn="T1157")
    assert cast and chose
    assert _power(e, "T1157") == 4000
    assert _power(e, "T030") == 2000


def test_opponent_creatures_are_not_candidates(rules):
    """判別: 相手のクリーチャーは候補に入らない
    （owner: you）。自分のクリーチャーが無ければ
    修整は生成されず、ドローだけが解決する。"""
    e, cast, _, hand0 = _cast(
        rules,
        {"hand": ["T1163"], "mana": ["T001"] * 3},
        {"bz": ["T030"]})
    assert cast
    assert _power(e, "T030", p=1) == 2000   # 相手の多色は不変
    assert _count(e, "hand", 0) == hand0   # ドローは解決する
    assert "T1163" in _defns(e, "graveyard", 0)


def test_no_creature_still_draws(rules):
    """実挙動: どちらのバトルゾーンにもクリーチャーが
    無ければ、修整なしでドローだけが解決する
    （civ_count は空の ref で 0＝p_up 0）。"""
    e, cast, _, hand0 = _cast(
        rules,
        {"hand": ["T1163"], "mana": ["T001"] * 3})
    assert cast
    assert _count(e, "hand", 0) == hand0
    assert "T1163" in _defns(e, "graveyard", 0)


def test_bonus_expires_at_end_of_turn(rules):
    """実挙動: 修整は duration: end_of_turn で、
    ターンが終われば元のパワーに戻る。"""
    e, cast, _, _ = _cast(
        rules,
        {"hand": ["T1163"], "mana": ["T001"] * 3, "bz": ["T030"]},
        choose_defn="T030")
    assert cast
    assert _power(e, "T030") == 6000
    # 自分のターンを終え、相手ターンも進めて、自分の
    # 次のターンの判断まで進める
    seen_next_main = False
    for _ in range(1200):
        d = e.advance()
        if d is None:
            break
        if d["kind"] == "main" and d.get("player") == 0:
            seen_next_main = True
            break
        e.answer(_boring(d))
    assert seen_next_main
    assert _power(e, "T030") == 2000
