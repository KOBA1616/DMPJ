"""語彙パイロット第368弾: draw_equal_to_chosen_cost
（ドリフト）。

センサス（rejects 1,965件を取り直し）: pure 1,818件 /
multi 129行 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
106 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
（pure/multi の数え方は第367弾までと同じ重複除去後の
gaps 長: dm25ex2-057 は gaps が [hyperdimensional_zone
×2] の重複行のため pure 扱い、33-sec001 は
[god_slayer, select_min_power ×2] のため multi 扱い。
生の長さで数えると pure 1,817 / multi 130 になる。）
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜367弾）は再提案しない。本弾で個別に
評価して見送った候補: battle_indestructible（pure 1、
dmd27-012。text・partial ともに空で評価不能＝
fixed_breaks_plus_one と同型）、static_double_power
（pure 1、dmrp19-008。「バトル中だけ2倍」は power_when に
バトル中のスコープが無く、static の double_power は
第141弾の注記どおり範囲固定の modify 専用で常在の
バトル限定倍化にはならない＝新語彙が要る）、
indestructible_while_blocking（pure 1、dmrp22-029。
battle_indestructible はバトル全般に効き「ブロック中」
限定にはならず、partial のコスト軽減 static も壊れて
いる）、must_be_blocked（pure 1、dmex08-291。
must_be_attacked は攻撃先の強制でブロックの強制とは
別機構）、abilities_cannot_be_used（pure 1、dm11-015。
deny のアクションに能力使用が無くエンジン側の概念が
要る）、ex_life_trigger / trigger_when_chosen（各 pure 1。
追加ターンの付与と複合条項が残り最小でない）、
saver_race_grant（pure 1。種族パラメータつきセイバーの
付与語彙が無い）。範囲内・未評価で最小の
draw_equal_to_chosen_cost（pure 1件、multi にも
現れない）を選定した。

対象は pure 1件すべて: dm21-011 グレート・リンク・
テクノロジー（水の呪文、コスト10）。partial は骨格
（types [spell] / civs [water] / cost 10、abilities・
spell ともに無し）で、未解決は unsupported の
draw_equal_to_chosen_cost 1件だけ（partial の注記
「選んだカードの『コスト』を枚数として参照する式が
無いため unsupported に残した（シンパシー自体は
書ける）」）。単面カードで未検証の面は無い。条項は
すべて確立済みの部品で表せる（追加語彙なし）:

- シンパシー「自分のグレートメカオーまたは
  キカイヒーロー1体につき1少なくなる。ただしコストは
  1より少なくならない」は同セットの登録先例 dm21-020
  と同形: static {kind: static, zone: hand, affects:
  self, mod: {cost: {amount: -1, count: {zone: bz,
  owner: you, filter: {races: [グレートメカオー,
  キカイヒーロー]}}}, cost_min: 1}}。
- 「バトルゾーンにあるクリーチャーを1体選ぶ」は
  choose {select: {zone: bz, owner: any, filter:
  {types: [creature]}, count: 1}, as: pick}
  （セレクタの owner 既定は you のため、自他どちらも
  選べるように owner: any を明示する。converted に
  多数の使用例がある）。
- 「そのクリーチャーのコストの数と同じ枚数のカードを
  引く」は draw {count: {cost_of: pick}}。cost_of は
  selectors の一般式で、束縛変数の参照は move の
  as ＋ filter の cost_of の登録先例 dm26ex1-029 と
  同じ仕組み。対象が居なければ cost_of は 0 で
  引かない（公式どおり）。

確立形: abilities = [シンパシーの static]、
spell = [choose {as: pick}, draw {count:
{cost_of: pick}}]。

proto T1108（dm21-011 型）/ T1109（グレートメカオー・
コスト3役）/ T1110（キカイヒーロー・コスト5役）/
T1111（対象外種族・コスト7役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED
が復活するので scenario.build を直接包む
（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

SYMPATHY = {"kind": "static", "zone": "hand", "affects": "self",
            "mod": {"cost": {"amount": -1,
                             "count": {"zone": "bz", "owner": "you",
                                       "filter": {"races": ["グレートメカオー",
                                                            "キカイヒーロー"]}}},
                    "cost_min": 1}}
SPELL = [{"op": "choose",
          "select": {"zone": "bz", "owner": "any",
                     "filter": {"types": ["creature"]},
                     "count": 1},
          "as": "pick"},
         {"op": "draw", "count": {"cost_of": "pick"}}]
FORM_ABILITIES = [SYMPATHY]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1108")
    assert c["abilities"] == FORM_ABILITIES
    assert c["spell"] == SPELL
    assert c["types"] == ["spell"] and c["civs"] == ["water"]
    assert c["cost"] == 10
    d = parse_card(copy.deepcopy(c), TABLES)
    assert SYMPATHY in d.abilities
    assert [op["op"] for op in d.spell] == ["choose", "draw"]
    assert d.spell[0]["as"] == "pick"
    assert d.spell[1]["count"] == {"cost_of": "pick"}
    for tid in ("T1109", "T1110", "T1111"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX368", "name": "x",
                    "types": ["spell"], "civs": ["water"],
                    "cost": 10, "mana": 1,
                    "abilities": copy.deepcopy(FORM_ABILITIES),
                    "spell": copy.deepcopy(SPELL)}, TABLES)
    assert SYMPATHY in d.abilities
    assert [op["op"] for op in d.spell] == ["choose", "draw"]


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _hand_spell(e):
    return next(c for c in e.zlist("hand", 0)
                if e.cdef(c).id == "T1108")


def test_sympathy_pay_cost(rules):
    """特性レベル: シンパシーは自分のグレートメカオー／
    キカイヒーロー1体につき -1（相手のもの・対象外種族は
    数えない）。"""
    e = _build(rules, {"hand": ["T1108"]}, {})
    assert e.chars(_hand_spell(e))["pay_cost"] == 10
    e = _build(rules, {"hand": ["T1108"], "bz": ["T1109"]}, {})
    assert e.chars(_hand_spell(e))["pay_cost"] == 9
    e = _build(rules, {"hand": ["T1108"], "bz": ["T1109", "T1110"]}, {})
    assert e.chars(_hand_spell(e))["pay_cost"] == 8
    e = _build(rules, {"hand": ["T1108"]}, {"bz": ["T1109", "T1110"]})
    assert e.chars(_hand_spell(e))["pay_cost"] == 10   # 相手のは数えない
    e = _build(rules, {"hand": ["T1108"], "bz": ["T1111"]}, {})
    assert e.chars(_hand_spell(e))["pay_cost"] == 10   # 対象外種族


def test_sympathy_pay_cost_floor(rules):
    """特性レベル: コストは1より少なくならない
    （cost_min: 1）。"""
    e = _build(rules, {"hand": ["T1108"], "bz": ["T1109"] * 12}, {})
    assert e.chars(_hand_spell(e))["pay_cost"] == 1


def _boring(d):
    keys = [o["key"] for o in d["options"]]
    for want in ("pass", "end_turn", "end_attack", "end_phase"):
        if want in keys:
            return [keys.index(want)]
    return [0]


def _cast(rules, p0, p1, choose_defn):
    """p0 が T1108 を唱え、choose_defn を選んで解決まで
    進める。（唱えたか, choose の min, 唱える直前の手札数,
    解決後の手札数, 場の状態）を返す。"""
    e = _build(rules, p0, p1)
    cast = False
    chose_min = None
    hand_before = None
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not cast and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T1108" in keys:
            hand_before = len(e.zlist("hand", 0))
            cast = True
            e.answer([keys.index("play:T1108")])
            continue
        if cast and d["kind"] == "choose_cards":
            chose_min = d["min"]
            idx = [i for i, o in enumerate(d["options"])
                   if choose_defn in o["key"]]
            assert idx, f"{choose_defn} が選択肢に無い: {keys}"
            e.answer(idx[:1])
            continue
        if cast and d["kind"] in ("main", "charge", "attack"):
            break          # 解決が終わり次の通常判断に戻った
        e.answer(_boring(d))
    hand_after = len(e.zlist("hand", 0))
    return e, cast, chose_min, hand_before, hand_after


def test_cast_choose_own_creature_draws_its_cost(rules):
    """自分のコスト5（キカイヒーロー）を選ぶと5枚引く。
    唱えた呪文は墓地に置かれる。候補が1体だけの時は
    選択判断が出ず自動で決まる（選択が必須であることは
    候補2体の test_cast_with_sympathy_discount で
    min=1 として固定）。"""
    e, cast, chose_min, hb, ha = _cast(
        rules,
        {"hand": ["T1108"], "mana": ["T1109"] * 10, "bz": ["T1110"]},
        {}, "T1110")
    assert cast
    assert ha == hb - 1 + 5
    assert "T1108" in [e.cdef(c).id for c in e.zlist("graveyard", 0)]


def test_cast_choose_opponent_creature_draws_its_cost(rules):
    """相手のコスト7のクリーチャーを選んでもよい
    （owner の指定が無い選択）。7枚引く。"""
    e, cast, chose_min, hb, ha = _cast(
        rules,
        {"hand": ["T1108"], "mana": ["T1109"] * 10},
        {"bz": ["T1111"]}, "T1111")
    assert cast
    assert ha == hb - 1 + 7


def test_cast_with_sympathy_discount(rules):
    """実フロー: 自分のグレートメカオー＋キカイヒーローが
    場にいれば支払いは8で足り、そのまま唱えてコスト3の
    グレートメカオーを選んで3枚引く。"""
    e, cast, chose_min, hb, ha = _cast(
        rules,
        {"hand": ["T1108"], "mana": ["T1109"] * 8,
         "bz": ["T1109", "T1110"]},
        {}, "T1109")
    assert cast and chose_min == 1
    assert ha == hb - 1 + 3


def test_cast_with_no_creature_draws_zero(rules):
    """バトルゾーンにクリーチャーが居なければ選べず、
    0枚引く（呪文自体は解決され墓地に置かれる）。"""
    e, cast, chose_min, hb, ha = _cast(
        rules,
        {"hand": ["T1108"], "mana": ["T1109"] * 10},
        {}, "T1109")
    assert cast and chose_min is None    # 選択判断自体が出ない
    assert ha == hb - 1
    assert "T1108" in [e.cdef(c).id for c in e.zlist("graveyard", 0)]
