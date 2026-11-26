"""語彙パイロット第395弾: civ_count_of_destroyed（ドリフト）。

センサス（rejects 1,938件を取り直し）: pure 1,790件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜394弾）は再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021 と
battle_opponent_reference の残り1件 dmr01-049 は
先行弾の評価を覆す根拠が無く再提案しない。本弾で
個別に評価して見送った候補: destroyed_this_turn_
condition（pure 1、dm26ex2-mc012。第392・393弾の
次点だが依然として最小ではない: partial も reason も
無い素行の呪文で3条項あり、第1条項は手札ゾーンの
ターン終了時無償詠唱の付与で確立形が未検証のまま。
次点として残す）、power_per_civilization（pure 1、
dm25-055。本弾と同じ civ_count の ref 解決が核だが、
選んだ（破壊していない）クリーチャーの文明数を
modify の power amount に {mul} で掛ける位置の検証が
追加で要り、本弾の後続候補として残す）、
distinct_civ_count（pure 1、dmx19-s45。CIP の
文明数ドロー＋常在パワー＋全文明でのワールド・
ブレイカー付与の3条項で、本弾より重い。後続候補）、
keyword_exists_condition（pure 1、dmr07-010。
キーワード所持での exists / フィルタは未検証の
別系統〈has_ability_filter 等〉が要る）、
enters_tapped_grant（pure 1、dm26ex3-010。第2条項は
第384弾の enters_tapped 付与形だが、第3条項
〈相手の効果で手札から捨てられる時にかわりに出す〉が
partial の abilities にも unsupported にも無く、
第379・385弾で却下された madness 系の捨て置換照合が
要るため本 gap 単独では登録形が定まらない）、
first_attack_this_turn_condition（pure 1、
dm22ex1-004。勝利条件条項が同居）、turn_destroyed_
count（pure 1、dm26rp2-std008。追加ターン付与まで
含む複合）。範囲内・最小の civ_count_of_destroyed
（pure 1件、multi にも現れない）を選定した。

対象は pure 1件すべて: dmex15-b099 生魂転霊
（自然の呪文 / コスト2 / S・トリガー）。partial は
骨格（types [spell] / civs [nature] / cost 2 /
mana 1、keywords [s_trigger]、abilities・spell
ともに無し）で、未解決は unsupported の
civ_count_of_destroyed 1件だけ。partial の text は
行の公式テキスト全文と一致する（補完なし）。
alias は dm24-110 / promoy24-026 の2件で、いずれも
rejects に独自行は無く、第395弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも登録なし。
単面カードで未検証の面は無い。

条項「自分のクリーチャーを１体破壊する。その後、
そのクリーチャーが持っていた文明の数だけ、自分の
山札の上からカードをマナゾーンに置く」はすべて
確立済みの部品で表せる（追加語彙なし）:

- 「自分のクリーチャーを１体破壊する」は choose
  {select: {zone: bz, owner: you, filter:
  {types: [creature]}, count: 1}, as: victim}
  （第368・385弾の choose 確立形。所有者は you）
  → destroy {select: {ref: victim}}（マクロ:
  move {to: graveyard, reason: destroy}）。
- 「そのクリーチャーが持っていた文明の数」は
  第79弾の式 civ_count に {ref: victim} セレクタを
  渡す形。civ_count の引数はセレクタ一般で、defs の
  expr 検証は selector として検証し、schema.py でも
  civ_count: ref("selector")、selector の ref キー、
  from_top: ref("expr") と両側に定義済みであることを
  確認した（第408ラウンドの教訓）。ただし実挙動の
  検証で、candidates の ref 分岐は alive（gen 一致）
  で絞るため、破壊で gen が進んだ後の {ref: victim}
  は空になり civ_count は 0 に倒れることが判明した
  （第389弾の cost_of は _expr_refs 経由で gen を
  見ないため移動後も読めたが、civ_count は
  candidates 経由で事情が異なる。第394弾で次点に
  留めた未検証点の実測結果）。そこで第322弾の
  set_var（式を評価して束縛する op。登録先例に
  「捨てる前に set_var で手札枚数を数えてから使う」
  形がある）で、破壊前に civ_count {ref: victim} を
  数えて束縛し、mana_put の from_top に {var: n_civs}
  で渡す——「移動前に数えて束縛する」確立パターンの
  適用で、追加語彙は無い。
- 「自分の山札の上からカードをマナゾーンに置く」は
  mana_put マクロ {select: {zone: deck, owner: you,
  from_top: {var: n_civs}}}（move {to: mana,
  reason: put} への展開。from_top の式評価は
  第389弾で検証済み）。
- 破壊できなかった場合（離れない等）でも文面の
  参照先は選んだクリーチャーであり、破壊前に
  数えた文明数を使う本形と一致する。候補が無ければ
  choose は空で civ_count は 0＝0枚（第368・385弾の
  cost_of 0 と同じ読み）。

確立形: spell = [choose {owner: you, as: victim},
set_var {name: n_civs, value: {civ_count:
{ref: victim}}}, destroy {ref: victim}, mana_put
{from_top: {var: n_civs}}] の4 op。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['s_trigger'], 条項テキスト, [])
を返し、part[2] の定型所有は空＝ブロッカー無し
（本弾で実測）。

proto T1162（dmex15-b099 型）。判別役は既存 proto を
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
          "as": "victim"},
         {"op": "set_var", "name": "n_civs",
          "value": {"civ_count": {"ref": "victim"}}},
         {"op": "destroy", "select": {"ref": "victim"}},
         {"op": "mana_put",
          "select": {"zone": "deck", "owner": "you",
                     "from_top": {"var": "n_civs"}}}]
FORM = SPELL
# parse_card はマクロを展開するため、検証後の spell は
# destroy → move {to: graveyard, reason: destroy}、
# mana_put → move {to: mana, reason: put} の展開形に
# なる（set_var はマクロでないのでそのまま。本弾で実測）
EXPANDED = [SPELL[0], SPELL[1],
            {"op": "move", "select": {"ref": "victim"},
             "to": "graveyard", "reason": "destroy"},
            {"op": "move",
             "select": {"zone": "deck", "owner": "you",
                        "from_top": {"var": "n_civs"}},
             "to": "mana", "reason": "put"}]
FULL_TEXT = ("S・トリガー（この呪文をシールドゾーンから手札に加える時、"
             "コストを支払わずにすぐ唱えてもよい）\n"
             "自分のクリーチャーを１体破壊する。その後、その"
             "クリーチャーが持っていた文明の数だけ、自分の山札の"
             "上からカードをマナゾーンに置く。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1162")
    assert c["name"] == "生魂転霊"
    assert c["types"] == ["spell"]
    assert c["civs"] == ["nature"]
    assert c["cost"] == 2 and c["mana"] == 1
    assert c["keywords"] == ["s_trigger"]
    assert not c.get("abilities")
    assert c["text"] == FULL_TEXT
    assert c["spell"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.spell == EXPANDED          # マクロ展開後の形
    for tid in ("T030", "T1157", "T001"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX395", "name": "x",
                    "types": ["spell"], "civs": ["nature"],
                    "cost": 2, "mana": 1,
                    "keywords": ["s_trigger"],
                    "spell": copy.deepcopy(FORM)}, TABLES)
    assert d.spell == EXPANDED


def test_bad_forms_rejected(rules):
    # 未知の op 名は DefError（expand_ops の検証）
    bad = copy.deepcopy(proto_card("T1162"))
    bad["spell"][2] = {"op": "destroyx", "select": {"ref": "victim"}}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # choose の select の未知キーは DefError
    bad2 = copy.deepcopy(proto_card("T1162"))
    bad2["spell"][0]["select"]["bogus"] = 1
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)
    # mana_put への未知の引数は展開先の move の検証で DefError
    bad3 = copy.deepcopy(proto_card("T1162"))
    bad3["spell"][3]["bogus"] = 1
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


def _boring(d):
    keys = [o["key"] for o in d["options"]]
    for want in ("pass", "end_turn", "end_attack", "end_phase"):
        if want in keys:
            return [keys.index(want)]
    return [0]


def _cast(rules, p0, p1=None, choose_defn=None):
    """p0 が T1162 を唱え、choose が出れば choose_defn を
    選んで解決まで進める。（engine, 唱えたか, choose
    判断が出たか, 詠唱直前の (マナ数, 山札数)) を返す。
    山札は初期手札ドロー等で減るため、枚数の検証は
    詠唱直前との差分で行う。"""
    e = _build(rules, p0, p1)
    cast = False
    chose = False
    base = None
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not cast and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T1162" in keys:
            cast = True
            base = (_count(e, "mana", 0), _count(e, "deck", 0))
            e.answer([keys.index("play:T1162")])
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
    return e, cast, chose, base


def test_cast_multicolor_destroys_and_puts_two(rules):
    """実挙動: 多色クリーチャー（光・水＝文明2つ）の
    T030 を選んで破壊すると、山札の上から2枚が
    マナゾーンに置かれる（破壊前に set_var で数えた
    civ_count {ref: victim} が 2 になることの検証。
    破壊後に直接数える形では gen 不一致で 0 に
    倒れることを本弾で実測済み）。候補が1体だけの
    時は choose 判断が出ず自動で選ばれる（本弾で
    実測）。"""
    e, cast, chose, (mana0, deck0) = _cast(
        rules,
        {"hand": ["T1162"], "mana": ["T001"] * 2, "bz": ["T030"]},
        choose_defn="T030")
    assert cast and not chose   # 候補1体では自動選択
    assert "T030" not in _defns(e, "bz", 0)
    assert "T030" in _defns(e, "graveyard", 0)
    assert _count(e, "mana", 0) == mana0 + 2   # 置いた2枚分増える
    assert _count(e, "deck", 0) == deck0 - 2
    assert "T1162" in _defns(e, "graveyard", 0)


def test_cast_monocolor_puts_one(rules):
    """実挙動: 単色クリーチャー（火＝文明1つ）の
    T1157 を破壊すると、置かれるのは1枚だけ
    （候補1体では自動選択）。"""
    e, cast, chose, (mana0, deck0) = _cast(
        rules,
        {"hand": ["T1162"], "mana": ["T001"] * 2, "bz": ["T1157"]},
        choose_defn="T1157")
    assert cast and not chose   # 候補1体では自動選択
    assert "T1157" in _defns(e, "graveyard", 0)
    assert _count(e, "mana", 0) == mana0 + 1
    assert _count(e, "deck", 0) == deck0 - 1


def test_choice_determines_count(rules):
    """判別: 候補が2体（単色 T1157 と多色 T030）いて
    多色を選ぶと2枚置かれ、選ばなかった単色は残る。
    数は選んだ（破壊した）カードの文明数に従う。"""
    e, cast, chose, (mana0, deck0) = _cast(
        rules,
        {"hand": ["T1162"], "mana": ["T001"] * 2,
         "bz": ["T1157", "T030"]},
        choose_defn="T030")
    assert cast and chose
    assert "T030" in _defns(e, "graveyard", 0)
    assert "T1157" in _defns(e, "bz", 0)
    assert _count(e, "mana", 0) == mana0 + 2
    assert _count(e, "deck", 0) == deck0 - 2


def test_opponent_creatures_are_not_candidates(rules):
    """判別: 相手のクリーチャーは候補に入らない
    （owner: you）。自分のクリーチャーが無ければ
    何も破壊されず、マナも増えない。"""
    e, cast, _, (mana0, deck0) = _cast(
        rules,
        {"hand": ["T1162"], "mana": ["T001"] * 2},
        {"bz": ["T1157"]})
    assert cast
    assert "T1157" in _defns(e, "bz", 1)
    assert _count(e, "mana", 0) == mana0
    assert _count(e, "deck", 0) == deck0
    assert "T1162" in _defns(e, "graveyard", 0)


def test_no_creature_resolves_empty(rules):
    """実挙動: どちらのバトルゾーンにもクリーチャーが
    無ければ、呪文は空で解決する（civ_count は
    空の ref で 0＝0枚）。"""
    e, cast, _, (mana0, deck0) = _cast(
        rules,
        {"hand": ["T1162"], "mana": ["T001"] * 2})
    assert cast
    assert _count(e, "mana", 0) == mana0
    assert _count(e, "deck", 0) == deck0
    assert "T1162" in _defns(e, "graveyard", 0)
